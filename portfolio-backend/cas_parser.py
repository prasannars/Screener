import casparser
import pdfplumber
import re
from typing import List, Dict, Optional
from casparser.exceptions import CASParseError, IncorrectPasswordError


def _to_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _holdings_from_casparser(data) -> List[Dict]:
    holdings: List[Dict] = []

    for folio in getattr(data, "folios", []) or []:
        for scheme in getattr(folio, "schemes", []) or []:
            valuation = getattr(scheme, "valuation", None)
            units = _to_float(getattr(scheme, "close", 0))
            nav = _to_float(getattr(valuation, "nav", 0) if valuation else 0)
            value = _to_float(getattr(valuation, "value", 0) if valuation else 0)
            cost = _to_float(getattr(valuation, "cost", 0) if valuation else 0)
            if units <= 0 and value <= 0:
                continue
            item = {
                "scheme_name": (getattr(scheme, "scheme", None) or "Unknown Scheme").strip(),
                "folio": str(getattr(folio, "folio", "Unknown")),
                "units": round(units, 3),
                "current_nav": round(nav, 2),
                "current_value": round(value, 2),
            }
            if cost > 0:
                item["invest_val"] = round(cost, 2)
                item["buy_price"] = round(cost / units, 2) if units else 0.0
            holdings.append(item)

    for account in getattr(data, "accounts", []) or []:
        for mf in getattr(account, "mutual_funds", []) or []:
            units = _to_float(getattr(mf, "balance", 0))
            nav = _to_float(getattr(mf, "nav", 0))
            value = _to_float(getattr(mf, "value", 0))
            cost = _to_float(getattr(mf, "total_cost", 0))
            if units <= 0 and value <= 0:
                continue
            item = {
                "scheme_name": (getattr(mf, "name", None) or "Unknown Scheme").strip(),
                "folio": str(getattr(mf, "folio", None) or getattr(account, "client_id", None) or "Unknown"),
                "units": round(units, 3),
                "current_nav": round(nav, 2),
                "current_value": round(value, 2),
            }
            if cost > 0:
                item["invest_val"] = round(cost, 2)
                item["buy_price"] = round(cost / units, 2) if units else 0.0
            holdings.append(item)

    return holdings


def _parse_cas_heuristic(file_path: str, password: Optional[str] = None) -> List[Dict]:
    holdings = []
    with pdfplumber.open(file_path, password=password or "") as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for i, line in enumerate(lines):
                if not re.search(r"Folio", line, re.IGNORECASE):
                    continue

                folio_match = re.search(
                    r"Folio\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Za-z0-9][\w\-/ ]*)",
                    line,
                    re.IGNORECASE,
                )
                if not folio_match:
                    continue

                folio = folio_match.group(1).strip()
                scheme_name = "Unknown Scheme"
                if i > 0:
                    prev_line = lines[i - 1]
                    if not re.search(r"Folio|NAV|Units|Value|Date|PAN|Page", prev_line, re.IGNORECASE):
                        scheme_name = prev_line

                context = " ".join(lines[i : i + 8])
                units_match = re.search(
                    r"(?:Closing\s*(?:Unit\s*)?Balance|Closing\s*Units|Units)\s*[:\-]?\s*([\d,]+\.?\d*)",
                    context,
                    re.IGNORECASE,
                )
                nav_match = re.search(r"NAV\s*[:\-]?\s*([\d,]+\.?\d*)", context, re.IGNORECASE)
                value_match = re.search(
                    r"(?:Market\s*Value|Current\s*Value|Valuation|Value)\s*[:\-]?\s*([\d,]+\.?\d*)",
                    context,
                    re.IGNORECASE,
                )

                units = _to_float(units_match.group(1) if units_match else 0)
                nav = _to_float(nav_match.group(1) if nav_match else 0)
                value = _to_float(value_match.group(1) if value_match else 0)

                if units > 0 or value > 0:
                    holdings.append({
                        "scheme_name": scheme_name.strip(),
                        "folio": folio,
                        "units": round(units, 3),
                        "current_nav": round(nav, 2),
                        "current_value": round(value, 2),
                    })

    unique_holdings = {}
    for h in holdings:
        key = f"{h['scheme_name'].lower()}_{h['folio']}"
        if key not in unique_holdings or h["current_value"] > unique_holdings[key]["current_value"]:
            unique_holdings[key] = h
    return list(unique_holdings.values())


def parse_cas_pdf(file_path: str, password: Optional[str] = None) -> List[Dict]:
    """
    Parse a CAMS / KFintech / NSDL / CDSL CAS PDF.
    Original issuer PDFs are usually password-protected (PAN or user password).
    """
    try:
        data = casparser.read_cas_pdf(file_path, password or "")
        holdings = _holdings_from_casparser(data)
        if holdings:
            return holdings
    except IncorrectPasswordError:
        raise IncorrectPasswordError(
            "This CAS PDF is password-protected. Enter your PAN (CAMS/NSDL/CDSL) "
            "or the password you set when requesting the statement (KFintech)."
        )
    except CASParseError as exc:
        # Fall back for some unlocked / slightly non-standard PDFs
        try:
            holdings = _parse_cas_heuristic(file_path, password)
            if holdings:
                return holdings
        except Exception:
            pass
        raise CASParseError(
            "Could not parse this file as an original CAMS/KFintech/NSDL/CDSL CAS. "
            "Re-download the statement from the issuer (do not print/save as a new PDF). "
            f"Details: {exc}"
        )

    try:
        holdings = _parse_cas_heuristic(file_path, password)
        if holdings:
            return holdings
    except Exception as exc:
        raise CASParseError(f"Failed to read PDF text: {exc}") from exc

    return []
