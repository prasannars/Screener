"""
Import a Consolidated Account Statement (CAS) PDF -- from CAMS, KFin,
NSDL, or CDSL -- into the existing portfolio_analyzer pipeline.

This module does not log in to MFCentral, does not handle OTPs, and does
not scrape anything. You get the CAS PDF yourself (MFCentral > Download
CAS, or CAMS/KFin's own "mailback" statement) and hand it to this module
along with its password (usually your PAN). From there it's just a file
parse, same as feeding portfolio_analyzer an Excel export.

Pipeline:
    CAS PDF + password
        -> casparser.read_cas_pdf()      (folios -> schemes -> transactions)
        -> cas_to_dataframe()            (flatten to the column names
                                           portfolio_analyzer.ALIASES already
                                           recognises)
        -> in-memory .xlsx bytes
        -> portfolio_analyzer.analyze_workbook()   (unchanged, reused as-is)

Usage (CLI):
    python cas_import.py statement.pdf
    python cas_import.py statement.pdf --password ABCDE1234F
    CAS_PASSWORD=ABCDE1234F python cas_import.py statement.pdf --out out.json

Usage (library):
    from cas_import import analyze_cas
    report = analyze_cas("statement.pdf", password="ABCDE1234F")
"""
from __future__ import annotations

import argparse
import getpass
import io
import json
import os
import re
import sys
from datetime import date

import pandas as pd

try:
    import casparser
    from casparser.enums import TransactionType
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "casparser is not installed. Run:\n"
        "    pip install casparser --break-system-packages"
    ) from exc

import portfolio_analyzer
from utils import get_logger, get_path

log = get_logger("cas_import")

# Transaction types that add units/money into a folio. Redemptions,
# switch-outs, and tax/STT lines are excluded -- casparser's own
# `valuation.cost` (the RTA's running cost basis) already nets those out,
# so we only fall back to summing these when a statement doesn't print a
# cost basis at all (seen on some NSDL/CDSL exports).
_INFLOW_TYPES = {
    TransactionType.PURCHASE,
    TransactionType.PURCHASE_SIP,
    TransactionType.SWITCH_IN,
    TransactionType.SWITCH_IN_MERGER,
}

# Column names deliberately match portfolio_analyzer.ALIASES so the
# existing header-sniffing / column-mapping code picks them up with zero
# changes to that file.
COLUMNS = [
    "Scheme Name", "AMC", "ISIN", "Folio", "Units", "Current NAV",
    "Current Value", "Invested Amount", "Date", "Mode",
]


# openpyxl rejects ASCII control chars (except tab/newline/cr) in cell values.
_ILLEGAL_EXCEL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _clean_text(value):
    if not isinstance(value, str):
        return value
    text = _ILLEGAL_EXCEL_RE.sub(" ", value).replace("#", " ")
    return re.sub(r"\s+", " ", text).strip()


def _amount(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # filter NaN


def _scheme_rows(folio, scheme) -> list[dict]:
    """One row per qualifying inflow transaction (dates only, for XIRR /
    holding-period calc) plus one summary row carrying units, NAV, current
    value, and total invested."""
    rows: list[dict] = []
    name = scheme.scheme
    amc = folio.amc
    isin = scheme.isin

    sip_count = 0
    inflow_sum = 0.0
    has_cost_fallback_txn = False
    for txn in scheme.transactions:
        if txn.type not in _INFLOW_TYPES:
            continue
        if txn.type == TransactionType.PURCHASE_SIP:
            sip_count += 1
        amt = _amount(txn.amount)
        txn_date = txn.date if isinstance(txn.date, date) else None
        if amt and amt > 0:
            inflow_sum += amt
            has_cost_fallback_txn = True
        if txn_date is None:
            continue
        # Date-only row: feeds the "dates" list portfolio_analyzer uses for
        # holding-period / CAGR estimation. Deliberately carries no
        # "Invested Amount" so it can't double-count against the summary
        # row's cost-basis figure below.
        rows.append({
            "Scheme Name": name,
            "AMC": amc,
            "ISIN": isin,
            "Folio": folio.folio,
            "Date": txn_date.isoformat(),
            "Mode": "SIP" if txn.type == TransactionType.PURCHASE_SIP else "Lump sum",
        })

    mode = "SIP" if sip_count >= 2 else "Lump sum"
    valuation = scheme.valuation
    cost = _amount(valuation.cost)
    value = _amount(valuation.value)
    units = _amount(scheme.close)
    nav = _amount(valuation.nav)

    summary_row = {
        "Scheme Name": name,
        "AMC": amc,
        "ISIN": isin,
        "Folio": folio.folio,
        "Units": units,
        "Current NAV": nav,
        "Current Value": value,
        "Mode": mode,
    }
    if cost:
        summary_row["Invested Amount"] = cost
    elif has_cost_fallback_txn:
        # Statement didn't print a cost basis (some NSDL/CDSL exports) --
        # fall back to summed inflows. This ignores redemption netting, so
        # it can overstate invested for partially-redeemed schemes.
        summary_row["Invested Amount"] = round(inflow_sum, 2)

    rows.append(summary_row)
    return rows


def _attr(obj, *names, default=None):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _is_demat_cas(cas_data) -> bool:
    """NSDL/CDSL statements expose demat `accounts`, not RTA `folios`."""
    return _attr(cas_data, "accounts") is not None and _attr(cas_data, "folios") is None


def _demat_to_rows(cas_data) -> tuple[list[dict], int]:
    """Flatten NSDL/CDSL mutual funds, equities, bonds, and NPS into analyzer rows."""
    rows: list[dict] = []
    skipped = 0
    for account in _attr(cas_data, "accounts") or []:
        amc = _attr(account, "name") or _attr(account, "type") or "Demat"
        folio = (
            _attr(account, "client_id")
            or _attr(account, "dp_id")
            or amc
        )

        for mf in _attr(account, "mutual_funds") or []:
            units = _amount(_attr(mf, "balance"))
            value = _amount(_attr(mf, "value"))
            if units in (None, 0) and value in (None, 0):
                skipped += 1
                continue
            cost = _amount(_attr(mf, "total_cost"))
            row = {
                "Scheme Name": _attr(mf, "name") or _attr(mf, "isin") or "Mutual Fund",
                "AMC": amc,
                "ISIN": _attr(mf, "isin"),
                "Folio": _attr(mf, "folio") or folio,
                "Units": units,
                "Current NAV": _amount(_attr(mf, "nav")),
                "Current Value": value,
                "Mode": "Lump sum",
            }
            if cost:
                row["Invested Amount"] = cost
            rows.append(row)

        for eq in _attr(account, "equities") or []:
            units = _amount(_attr(eq, "num_shares"))
            value = _amount(_attr(eq, "value"))
            if units in (None, 0) and value in (None, 0):
                skipped += 1
                continue
            rows.append({
                "Scheme Name": _attr(eq, "name") or _attr(eq, "symbol") or _attr(eq, "isin") or "Equity",
                "AMC": "Equity",
                "ISIN": _attr(eq, "isin"),
                "Folio": folio,
                "Units": units,
                "Current NAV": _amount(_attr(eq, "price")),
                "Current Value": value,
                "Mode": "Lump sum",
            })

        for bond in _attr(account, "bonds") or []:
            units = _amount(_attr(bond, "num_bonds"))
            value = _amount(_attr(bond, "value"))
            if units in (None, 0) and value in (None, 0):
                skipped += 1
                continue
            rows.append({
                "Scheme Name": _attr(bond, "name") or _attr(bond, "isin") or "Bond",
                "AMC": "Bond",
                "ISIN": _attr(bond, "isin"),
                "Folio": folio,
                "Units": units,
                "Current NAV": _amount(_attr(bond, "market_price") or _attr(bond, "face_value")),
                "Current Value": value,
                "Mode": "Lump sum",
            })

    nps = _attr(cas_data, "nps")
    if nps:
        for scheme in _attr(nps, "schemes") or []:
            units = _amount(_attr(scheme, "units"))
            value = _amount(_attr(scheme, "value"))
            if units in (None, 0) and value in (None, 0):
                skipped += 1
                continue
            rows.append({
                "Scheme Name": _attr(scheme, "scheme") or "NPS Scheme",
                "AMC": _attr(scheme, "fund_manager") or "NPS",
                "ISIN": None,
                "Folio": _attr(nps, "pran") or "NPS",
                "Units": units,
                "Current NAV": _amount(_attr(scheme, "nav")),
                "Current Value": value,
                "Mode": "Lump sum",
            })

    return rows, skipped


def _rta_to_rows(cas_data) -> tuple[list[dict], int]:
    rows: list[dict] = []
    skipped = 0
    for folio in _attr(cas_data, "folios") or []:
        for scheme in _attr(folio, "schemes") or []:
            valuation = _attr(scheme, "valuation")
            zero_units = _amount(_attr(scheme, "close")) in (None, 0)
            zero_value = _amount(_attr(valuation, "value") if valuation else None) in (None, 0)
            if zero_units and zero_value:
                skipped += 1
                continue
            rows.extend(_scheme_rows(folio, scheme))
    return rows, skipped


def cas_to_dataframe(cas_data) -> pd.DataFrame:
    """Flatten CAMS/KFin folios or NSDL/CDSL demat accounts into analyzer rows."""
    if _is_demat_cas(cas_data):
        rows, skipped = _demat_to_rows(cas_data)
    else:
        rows, skipped = _rta_to_rows(cas_data)
    if skipped:
        log.info(f"Skipped {skipped} zero-balance holding(s) (fully redeemed).")
    if not rows:
        raise ValueError("CAS parsed but contained no holdings with a non-zero balance.")
    rows = [{k: _clean_text(v) for k, v in row.items()} for row in rows]
    return pd.DataFrame(rows, columns=COLUMNS)


def _workbook_bytes(df: pd.DataFrame) -> bytes:
    cleaned = df.copy()
    for col in cleaned.select_dtypes(include=["object"]).columns:
        cleaned[col] = cleaned[col].map(_clean_text)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        cleaned.to_excel(writer, index=False, sheet_name="Holdings")
    return buf.getvalue()


def parse_cas(source, password: str, sort_transactions: bool = True):
    """Parse a CAS PDF via casparser. `source` is a file path, bytes, or an
    open file-like object -- never a stored MFCentral session."""
    if isinstance(source, (bytes, bytearray)):
        source = io.BytesIO(source)
    return casparser.read_cas_pdf(
        source, password, output="dict", sort_transactions=sort_transactions
    )


def analyze_cas(source, password: str, filename: str = "CAS statement.pdf",
                 catalog: list[dict] | None = None) -> dict:
    """Parse a CAS PDF and run it through the existing portfolio analyzer.
    Returns the same report shape analyze_workbook() would for an Excel
    upload, so it's a drop-in for anything already consuming that report
    (the dashboard, CLI, etc.)."""
    cas_data = parse_cas(source, password)
    if cas_data.parse_warnings:
        log.warning(
            f"casparser flagged {len(cas_data.parse_warnings)} data-quality "
            f"warning(s) -- treat affected schemes' figures with caution: "
            f"{cas_data.parse_warnings}"
        )
    df = cas_to_dataframe(cas_data)
    raw = _workbook_bytes(df)
    report = portfolio_analyzer.analyze_workbook(raw, "cas_import.xlsx", catalog)
    report["file"] = filename
    period = _attr(cas_data, "statement_period")
    file_type = _attr(cas_data, "file_type")
    cas_type = _attr(cas_data, "cas_type")
    folios = _attr(cas_data, "folios")
    accounts = _attr(cas_data, "accounts")
    report["source"] = {
        "kind": "CAS",
        "cas_type": getattr(cas_type, "value", None) or getattr(file_type, "value", None) or str(cas_type or file_type or "CAS"),
        "period_from": _attr(period, "from_", "from"),
        "period_to": _attr(period, "to"),
        "folios": len(folios) if folios is not None else len(accounts or []),
        "parse_warnings": _attr(cas_data, "parse_warnings") or [],
    }
    if cas_data.parse_warnings:
        report.setdefault("assumptions", []).append(
            f"casparser flagged {len(cas_data.parse_warnings)} scheme(s) where a transaction "
            "row may have been dropped or mis-parsed; treat those figures as approximate."
        )
    return report


def _load_catalog() -> list[dict]:
    try:
        import mutual_funds
        return mutual_funds.get_funds(refresh=False).get("rows") or []
    except Exception:
        log.warning("AMFI catalog unavailable; peer comparison will be thin.")
        return []


def _print_summary(report: dict) -> None:
    summary = report.get("summary") or {}
    print(f"\nFile: {report.get('file')}")
    src = report.get("source") or {}
    if src:
        print(f"CAS type: {src.get('cas_type')}  Period: {src.get('period_from')} -> {src.get('period_to')}  Folios: {src.get('folios')}")
    print(f"Schemes: {summary.get('funds')}")
    print(f"Invested: Rs {summary.get('invested', 0):,.0f}")
    print(f"Current value: Rs {summary.get('value', 0):,.0f}")
    print(f"Gain: Rs {summary.get('gain', 0):,.0f}  ({summary.get('ret_pct')}%)")
    if summary.get("xirr") is not None:
        print(f"XIRR (approx.): {summary.get('xirr')}%")
    print("\nHoldings:")
    for h in report.get("holdings") or []:
        print(f"  {h['name']:<55.55} value Rs {h.get('value', 0):>12,.0f}  gain {h.get('ret_pct')}%")


def main():
    ap = argparse.ArgumentParser(description="Parse a CAS PDF into the portfolio analyzer.")
    ap.add_argument("pdf", help="Path to the CAS PDF")
    ap.add_argument("--password", help="CAS PDF password (default: prompt, or $CAS_PASSWORD)")
    ap.add_argument("--out", help="Save the full JSON report to this path (default: output/cas_report_<date>.json)")
    args = ap.parse_args()

    if not os.path.exists(args.pdf):
        sys.exit(f"No such file: {args.pdf}")

    password = args.password or os.environ.get("CAS_PASSWORD") or getpass.getpass("CAS PDF password: ")
    catalog = _load_catalog()

    try:
        report = analyze_cas(args.pdf, password, filename=os.path.basename(args.pdf), catalog=catalog)
    except Exception as exc:
        sys.exit(f"Failed to parse/analyze CAS: {exc}")

    out_path = args.out or get_path(f"output/cas_report_{date.today().isoformat()}.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    _print_summary(report)
    print(f"\nFull report saved to {out_path}")


if __name__ == "__main__":
    main()
