"""
Parse an Indian mutual-fund Excel/CSV upload and build a structured report.

This is analysis of the file you provide, not SEBI-registered advice.
"""
from __future__ import annotations

import io
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta

import pandas as pd

from mutual_funds import cap_band

ALIASES = {
    "name": ("fund", "scheme", "fund name", "scheme name", "name", "particulars", "instrument"),
    "amc": ("amc", "fund house", "amc name", "house"),
    "isin": ("isin", "isin code"),
    "sip": ("sip", "sip amount", "monthly sip", "sip amt"),
    "date": ("date", "purchase date", "txn date", "investment date", "trans date", "nav date"),
    "units": ("units", "unit", "qty", "quantity", "no of units", "units held"),
    "nav": ("nav", "purchase nav", "avg nav", "average nav", "buy nav"),
    "current_nav": ("current nav", "latest nav", "ltp", "present nav"),
    "value": ("current value", "market value", "present value", "current amt", "value", "aum"),
    "invested": ("invested", "invested amount", "cost", "amount invested", "purchase value", "investment", "amount"),
    "gain": ("gain", "pnl", "p/l", "profit", "absolute gain", "unrealised"),
    "xirr": ("xirr", "cagr"),
    "ret_pct": ("return %", "returns %", "abs return", "absolute return %"),
    "category": ("category", "sub category", "sub-category", "type", "classification"),
    "kind": ("sip/lumpsum", "investment type", "mode", "transaction type", "txn type"),
}

NUM_KEYS = ("sip", "units", "nav", "current_nav", "value", "invested", "gain", "xirr", "ret_pct")

def _norm_header(value) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    text = text.replace("%", " %").replace("_", " ")
    return re.sub(r"[^a-z0-9 %/+-]", "", text).strip()

def _map_columns(headers: list[str]) -> dict[str, str]:
    mapped = {}
    used = set()
    for field, aliases in ALIASES.items():
        for header in headers:
            key = _norm_header(header)
            if header in used or not key:
                continue
            if key in aliases or any(alias == key or alias in key for alias in aliases):
                mapped[field] = header
                used.add(header)
                break
    return mapped

def _to_number(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text or text in ("-", "—", "NA", "N/A", "null"):
        return None
    text = text.replace(",", "").replace("₹", "").replace("%", "").replace("Rs.", "").replace("INR", "")
    text = re.sub(r"\((.+)\)", r"-\1", text)
    try:
        return float(text)
    except ValueError:
        return None

def _to_date(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and 20000 < value < 80000:
        try:
            return pd.to_datetime(value, unit="D", origin="1899-12-30").date()
        except Exception:
            return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(text, dayfirst=True).date()
    except Exception:
        return None

def _guess_bucket(name: str, category: str = "") -> str:
    text = f"{name} {category}".lower()
    if any(w in text for w in ("gilt", "liquid", "overnight", "money market", "debt", "bond", "gilt", "income", "gilt")):
        if "gilt" in text or "liquid" in text or "overnight" in text or "debt" in text or "bond" in text:
            if not any(w in text for w in ("hybrid", "balanced", "equity")):
                return "Debt"
    if any(w in text for w in ("international", "us ", "nasdaq", "global", "overseas")):
        return "International"
    if any(w in text for w in ("hybrid", "balanced", "multi asset", "arbitrage")):
        return "Hybrid"
    if "index" in text or "etf" in text:
        return "Index"
    if any(w in text for w in ("elss", "equity", "flexi", "large", "mid", "small", "value", "momentum", "sector", "thematic")):
        return "Equity"
    return "Other"

def _cap_band(name: str, category: str = "") -> str:
    return cap_band(name, category)

def _score_header_row(values) -> int:
    headers = [str(v) for v in values]
    return len(_map_columns(headers))

def _read_book(raw: bytes, filename: str) -> dict[str, pd.DataFrame]:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(raw))
        return {"Sheet1": df}
    try:
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None, engine="openpyxl")
    except Exception:
        book = pd.read_excel(io.BytesIO(raw), sheet_name=None, header=None)
    return book

def _frame_from_sheet(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str], int] | None:
    if raw is None or raw.empty:
        return None
    best_i, best_score = 0, -1
    limit = min(20, len(raw))
    for i in range(limit):
        score = _score_header_row(raw.iloc[i].tolist())
        if score > best_score:
            best_score, best_i = score, i
    if best_score < 2:
        return None
    headers = [str(v).strip() if pd.notna(v) else f"col_{j}" for j, v in enumerate(raw.iloc[best_i].tolist())]
    seen = {}
    uniq = []
    for h in headers:
        n = seen.get(h, 0)
        seen[h] = n + 1
        uniq.append(h if n == 0 else f"{h}_{n}")
    body = raw.iloc[best_i + 1:].copy()
    body.columns = uniq
    body = body.dropna(how="all")
    mapping = _map_columns(uniq)
    return body, mapping, best_score

def _row_from_series(series: pd.Series, mapping: dict[str, str]) -> dict | None:
    get = lambda field: series.get(mapping[field]) if field in mapping else None
    name = str(get("name") or "").strip()
    if not name or name.lower() in ("nan", "total", "grand total", "summary"):
        return None
    if name.lower().startswith("total"):
        return None
    row = {
        "name": name,
        "amc": str(get("amc") or "").strip() or None,
        "isin": str(get("isin") or "").strip() or None,
        "category": str(get("category") or "").strip() or None,
        "kind": str(get("kind") or "").strip() or None,
        "date": _to_date(get("date")),
    }
    for key in NUM_KEYS:
        row[key] = _to_number(get(key)) if key in mapping else None
    if row["invested"] is None and row["units"] and row["nav"]:
        row["invested"] = round(row["units"] * row["nav"], 2)
    if row["value"] is None and row["units"] and row["current_nav"]:
        row["value"] = round(row["units"] * row["current_nav"], 2)
    if row["gain"] is None and row["value"] is not None and row["invested"] is not None:
        row["gain"] = round(row["value"] - row["invested"], 2)
    if row["ret_pct"] is None and row["invested"] and row["gain"] is not None:
        row["ret_pct"] = round(row["gain"] / row["invested"] * 100, 2)
    row["bucket"] = _guess_bucket(name, row["category"] or "")
    row["cap"] = _cap_band(name, row["category"] or "")
    kind = (row["kind"] or "").lower()
    if row["sip"] and row["sip"] > 0:
        row["mode"] = "SIP"
    elif "sip" in kind:
        row["mode"] = "SIP"
    elif "lump" in kind:
        row["mode"] = "Lump sum"
    else:
        row["mode"] = "Unknown"
    if not row["amc"]:
        row["amc"] = name.split()[0]
    return row

def _xirr(flows: list[tuple[date, float]]) -> float | None:
    flows = [(d, a) for d, a in flows if d and a]
    if len(flows) < 2:
        return None
    if not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    t0 = min(d for d, _ in flows)

    def npv(rate: float) -> float:
        total = 0.0
        for d, amount in flows:
            years = (d - t0).days / 365.0
            total += amount / ((1 + rate) ** years)
        return total

    rate = 0.12
    for _ in range(80):
        f = npv(rate)
        f1 = npv(rate + 1e-5)
        deriv = (f1 - f) / 1e-5
        if abs(deriv) < 1e-12:
            break
        nxt = rate - f / deriv
        if nxt <= -0.99:
            nxt = -0.99
        if abs(nxt - rate) < 1e-7:
            rate = nxt
            break
        rate = nxt
    if rate < -0.9 or rate > 10:
        return None
    return round(rate * 100, 2)

def _pct(part, whole) -> float | None:
    if not whole:
        return None
    return round(part / whole * 100, 1)

def _inr(value) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)

_NAME_STOP = {
    "fund", "direct", "growth", "plan", "regular", "idcw", "the", "and", "of",
    "india", "indian", "ltd", "limited", "option", "scheme",
}

def _tokens(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in _NAME_STOP and len(w) > 2}

def _name_score(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    jaccard = inter / len(ta | tb)
    subset = 0.25 if ta <= tb or tb <= ta else 0.0
    return jaccard + subset

def _match_one(name: str, catalog: list[dict]) -> dict | None:
    best, best_s = None, 0.0
    for item in catalog:
        score = _name_score(name, item.get("name") or "")
        if score > best_s:
            best, best_s = item, score
    if best_s < 0.42:
        return None
    return best

def _match_catalog(rows: list[dict], catalog: list[dict] | None):
    if not catalog:
        return
    for row in rows:
        hit = _match_one(row["name"], catalog)
        if not hit:
            continue
        row["amfi_code"] = hit.get("code")
        row["amfi_name"] = hit.get("name")
        if not row.get("amc"):
            row["amc"] = hit.get("amc")
        if hit.get("category"):
            row["category"] = hit["category"]
            row["bucket"] = hit.get("bucket") or row["bucket"]
            row["cap"] = _cap_band(row["name"], hit["category"])
        row["peer_1y"] = hit.get("ret_1y")
        row["peer_3y"] = hit.get("ret_3y")
        row["peer_5y"] = hit.get("ret_5y")
        row["peer_ai"] = hit.get("ai_score")
        row["peer_quality"] = hit.get("quality")
        row["peer_depth"] = hit.get("ai_depth")

def _open_direct_growth(item: dict) -> bool:
    if item.get("scheme_type") and item.get("scheme_type") != "Open Ended":
        return False
    if item.get("plan") and item.get("plan") != "Direct":
        return False
    if item.get("option") and item.get("option") != "Growth":
        return False
    return True

def _peer_metric(item: dict) -> float:
    ai = item.get("ai_score")
    r1 = item.get("ret_1y")
    r3 = item.get("ret_3y")
    score = (float(ai) if ai is not None else 0.45) * 0.55
    if r1 is not None:
        score += max(-20.0, min(40.0, float(r1))) / 40.0 * 0.25
    if r3 is not None:
        score += max(-10.0, min(28.0, float(r3))) / 28.0 * 0.20
    return score

def _same_group(holding: dict, item: dict) -> bool:
    hcat = (holding.get("category") or "").strip().lower()
    icat = (item.get("category") or "").strip().lower()
    if hcat and icat:
        return hcat == icat or hcat in icat or icat in hcat
    return (holding.get("bucket") == item.get("bucket")
            and _cap_band(item.get("name") or "", item.get("category") or "") == holding.get("cap"))

def compare_to_peers(holdings: list[dict], catalog: list[dict] | None) -> dict:
    """Rank each holding against Direct Growth peers in the same AMFI group."""
    catalog = catalog or []
    usable = [c for c in catalog if _open_direct_growth(c) and c.get("name")]
    held_tokens = [_tokens(h["name"]) for h in holdings]
    held_codes = {h.get("amfi_code") for h in holdings if h.get("amfi_code")}

    def is_held(item: dict) -> bool:
        if item.get("code") in held_codes:
            return True
        it = _tokens(item.get("name") or "")
        return any(len(it & ht) >= 3 for ht in held_tokens if ht)

    rows = []
    groups = {}
    codes = []
    for h in holdings:
        if h.get("amfi_code"):
            codes.append(h["amfi_code"])
        peers = [c for c in usable if _same_group(h, c)]
        if not peers:
            peers = [
                c for c in usable
                if c.get("bucket") == h.get("bucket")
                and _cap_band(c.get("name") or "", c.get("category") or "") == h.get("cap")
            ]
        scored = sorted(peers, key=_peer_metric, reverse=True)
        codes.extend(c.get("code") for c in scored[:12] if c.get("code"))
        yours = None
        if h.get("amfi_code"):
            yours = next((c for c in scored if c.get("code") == h["amfi_code"]), None)
        if yours is None:
            yours = _match_one(h["name"], scored) or _match_one(h["name"], usable)
        your_score = _peer_metric(yours) if yours else None
        rank = None
        if yours and scored:
            rank = next((i + 1 for i, c in enumerate(scored) if c.get("code") == yours.get("code")), None)
        alts = []
        for cand in scored:
            if is_held(cand) or (yours and cand.get("code") == yours.get("code")):
                continue
            if your_score is not None and _peer_metric(cand) < your_score + 0.04:
                continue
            bits = []
            if yours and cand.get("ret_1y") is not None and yours.get("ret_1y") is not None:
                gap = cand["ret_1y"] - yours["ret_1y"]
                if gap >= 2:
                    bits.append(f"1Y {gap:+.1f} pp vs yours")
            if yours and cand.get("ret_3y") is not None and yours.get("ret_3y") is not None:
                gap = cand["ret_3y"] - yours["ret_3y"]
                if gap >= 1:
                    bits.append(f"3Y {gap:+.1f} pp vs yours")
            if cand.get("ai_score") is not None:
                bits.append(f"AI {cand['ai_score']:.2f}")
            alts.append({
                "name": cand.get("name"),
                "amc": cand.get("amc"),
                "code": cand.get("code"),
                "ai": cand.get("ai_score"),
                "ret_1y": cand.get("ret_1y"),
                "ret_3y": cand.get("ret_3y"),
                "quality": cand.get("quality"),
                "reason": "; ".join(bits) or "Higher peer rank in this group.",
            })
            if len(alts) >= 3:
                break
        group_label = (yours or h).get("category") or h.get("bucket") or "Other"
        if yours and yours.get("ret_1y") is not None:
            h["peer_1y"] = yours.get("ret_1y")
            h["peer_3y"] = yours.get("ret_3y")
            h["peer_ai"] = yours.get("ai_score")
        verdict = "No peer data"
        if yours and rank:
            if not alts:
                verdict = "Keep — among the stronger names in this group"
            elif rank <= 5 and not alts:
                verdict = "Keep"
            elif alts and (your_score is None or _peer_metric(scored[0]) >= (your_score or 0) + 0.08):
                verdict = f"Consider {alts[0]['name']}"
            else:
                verdict = f"Hold, but #{rank} of {len(scored)} in group"
        elif alts:
            verdict = f"Look at {alts[0]['name']}"
        if "regular" in h["name"].lower() and "direct" not in h["name"].lower():
            verdict = "Switch this scheme to Direct first"
        rows.append({
            "name": h["name"],
            "matched": (yours or {}).get("name"),
            "group": group_label,
            "peer_n": len(scored),
            "rank": rank,
            "ai": (yours or h).get("ai_score") or h.get("peer_ai"),
            "ret_1y": (yours or h).get("ret_1y") if yours else h.get("peer_1y"),
            "ret_3y": (yours or h).get("ret_3y") if yours else h.get("peer_3y"),
            "verdict": verdict,
            "alts": alts,
        })
        pack = groups.setdefault(group_label, {"group": group_label, "yours": [], "leaders": []})
        pack["yours"].append(h["name"])
        if not pack["leaders"] and scored:
            pack["leaders"] = [{
                "name": c.get("name"),
                "amc": c.get("amc"),
                "ai": c.get("ai_score"),
                "ret_1y": c.get("ret_1y"),
                "ret_3y": c.get("ret_3y"),
                "held": is_held(c),
            } for c in scored[:3]]

    seen = []
    for code in codes:
        if code and code not in seen:
            seen.append(code)
    return {
        "note": (
            "Peers are open-ended Direct Growth schemes in the same AMFI category (or sleeve if category is missing). "
            "Rank uses PrasannaTrade fund AI plus 1Y/3Y when mfapi history is cached. Not a SEBI rating, and not advice."
        ),
        "rows": rows,
        "groups": list(groups.values()),
        "codes_needed": seen[:160],
        "compared": sum(1 for r in rows if r["rank"]),
    }

def apply_peer_advice(report: dict) -> dict:
    peer_rows = (report.get("peer") or {}).get("rows") or []
    by_name = {r["name"]: r for r in peer_rows}
    for item in report.get("advice") or []:
        peer = by_name.get(item["name"])
        if not peer or not peer.get("alts"):
            continue
        alt = peer["alts"][0]
        item["action"] = "Compare / switch SIP"
        item["why"] = (
            f"{peer['verdict']}. Better-ranked peer: {alt['name']}"
            + (f" ({alt['reason']})" if alt.get("reason") else "")
            + ". Check exit load, tax, and overlap before moving."
        )
        item["alt"] = alt["name"]
    actions = report.setdefault("verdict", {}).setdefault("actions", [])
    for peer in peer_rows:
        if peer.get("alts") and peer["rank"] and peer["rank"] > 8:
            line = f"In {peer['group']}, {peer['name']} is #{peer['rank']} of {peer['peer_n']}. Study {peer['alts'][0]['name']} before the next SIP."
            if line not in actions:
                actions.append(line)
    report["verdict"]["actions"] = actions[:6]
    return report

def analyze_workbook(raw: bytes, filename: str, catalog: list[dict] | None = None) -> dict:
    assumptions = []
    sheets_meta = []
    chosen = None
    book = _read_book(raw, filename)
    for sheet_name, raw_df in book.items():
        parsed = _frame_from_sheet(raw_df)
        if not parsed:
            sheets_meta.append({"sheet": sheet_name, "used": False, "reason": "Could not find a header row with fund columns."})
            continue
        frame, mapping, score = parsed
        rows = []
        for _, series in frame.iterrows():
            row = _row_from_series(series, mapping)
            if row:
                rows.append(row)
        sheets_meta.append({
            "sheet": sheet_name,
            "used": bool(rows),
            "columns": mapping,
            "rows": len(rows),
            "score": score,
        })
        if rows and (chosen is None or len(rows) > len(chosen[0])):
            chosen = (rows, mapping, sheet_name)

    if not chosen:
        raise ValueError(
            "No holdings table found. Need at least a fund/scheme name column plus invested amount, current value, or units."
        )

    txns, mapping, sheet_name = chosen
    assumptions.append(f"Read {len(txns)} rows from sheet “{sheet_name}”.")
    if "name" not in mapping:
        raise ValueError("Could not detect a fund name column.")
    if "invested" not in mapping and "value" not in mapping:
        assumptions.append("Invested or current value was missing on some rows; those rows stay in the list with blank money fields.")

    _match_catalog(txns, catalog)

    by_name: dict[str, dict] = {}
    flows: list[tuple[date, float]] = []
    for row in txns:
        key = (row.get("isin") or row["name"]).strip().lower()
        slot = by_name.setdefault(key, {
            "name": row["name"],
            "amc": row.get("amc"),
            "isin": row.get("isin"),
            "category": row.get("category"),
            "bucket": row["bucket"],
            "cap": row["cap"],
            "mode": row["mode"],
            "sip": 0.0,
            "units": 0.0,
            "invested": 0.0,
            "value": 0.0,
            "gain": 0.0,
            "xirr": row.get("xirr"),
            "ret_pct": None,
            "dates": [],
            "peer_1y": row.get("peer_1y"),
            "peer_3y": row.get("peer_3y"),
            "peer_ai": row.get("peer_ai"),
            "peer_5y": row.get("peer_5y"),
            "amfi_code": row.get("amfi_code"),
            "amfi_name": row.get("amfi_name"),
        })
        if row.get("amfi_code"):
            slot["amfi_code"] = row["amfi_code"]
            slot["amfi_name"] = row.get("amfi_name")
            slot["peer_1y"] = row.get("peer_1y")
            slot["peer_3y"] = row.get("peer_3y")
            slot["peer_ai"] = row.get("peer_ai")
            if row.get("category"):
                slot["category"] = row["category"]
                slot["bucket"] = row.get("bucket") or slot["bucket"]
                slot["cap"] = row.get("cap") or slot["cap"]
        if row.get("sip"):
            slot["sip"] += row["sip"]
            slot["mode"] = "SIP"
        if row.get("units"):
            slot["units"] += row["units"]
        if row.get("invested"):
            slot["invested"] += row["invested"]
        if row.get("value"):
            slot["value"] += row["value"]
        if row.get("date"):
            slot["dates"].append(row["date"])
            if row.get("invested"):
                flows.append((row["date"], -abs(row["invested"])))
        if row.get("xirr") is not None:
            slot["xirr"] = row["xirr"]
        if row.get("category"):
            slot["category"] = row["category"]

    holdings = []
    for slot in by_name.values():
        if slot["value"] and not slot["invested"] and slot["gain"]:
            slot["invested"] = slot["value"] - slot["gain"]
            assumptions.append(f"Invested for {slot['name']} inferred as current value minus gain.")
        if slot["invested"] and not slot["value"] and slot["gain"]:
            slot["value"] = slot["invested"] + slot["gain"]
        if slot["value"] and slot["invested"]:
            slot["gain"] = round(slot["value"] - slot["invested"], 2)
            slot["ret_pct"] = round(slot["gain"] / slot["invested"] * 100, 2) if slot["invested"] else None
        slot["sip"] = round(slot["sip"], 2) if slot["sip"] else None
        slot["units"] = round(slot["units"], 4) if slot["units"] else None
        slot["invested"] = _inr(slot["invested"]) or 0
        slot["value"] = _inr(slot["value"]) or 0
        slot["gain"] = _inr(slot["gain"]) or 0
        slot["first_date"] = min(slot["dates"]).isoformat() if slot["dates"] else None
        holdings.append(slot)

    holdings.sort(key=lambda r: r["value"] or r["invested"], reverse=True)
    invested = sum(h["invested"] or 0 for h in holdings)
    value = sum(h["value"] or 0 for h in holdings)
    gain = value - invested if value or invested else None
    ret_pct = round(gain / invested * 100, 2) if invested and gain is not None else None

    today = date.today()
    if value:
        flows.append((today, value))
    portfolio_xirr = _xirr(flows)
    if portfolio_xirr is None and ret_pct is not None:
        dates = [d for h in holdings for d in h.get("dates") or []]
        if dates:
            years = max((today - min(dates)).days / 365.25, 0.25)
            portfolio_xirr = round(((value / invested) ** (1 / years) - 1) * 100, 2) if invested and value > 0 else None
            assumptions.append(f"Portfolio XIRR was not in the file. CAGR-style annualised return uses {years:.1f} years from the earliest purchase date.")
        else:
            assumptions.append("No purchase dates, so portfolio XIRR could not be computed. Absolute return is shown instead.")

    sip_monthly = sum(h["sip"] or 0 for h in holdings)
    sip_value = sum(h["value"] for h in holdings if h["mode"] == "SIP")
    lump_value = sum(h["value"] for h in holdings if h["mode"] == "Lump sum")
    unknown_value = value - sip_value - lump_value

    def share(key, getter):
        groups = defaultdict(float)
        for h in holdings:
            groups[getter(h)] += h["value"] or h["invested"] or 0
        total = sum(groups.values()) or 1
        return sorted(
            [{"label": k, "amount": round(v, 2), "pct": round(v / total * 100, 1)} for k, v in groups.items()],
            key=lambda x: -x["amount"],
        )

    alloc_bucket = share("bucket", lambda h: h["bucket"])
    alloc_cap = share("cap", lambda h: h["cap"])
    alloc_amc = share("amc", lambda h: h["amc"] or "Unknown")

    equity_pct = sum(x["pct"] for x in alloc_bucket if x["label"] in ("Equity", "Index", "International"))
    debt_pct = next((x["pct"] for x in alloc_bucket if x["label"] == "Debt"), 0)
    hybrid_pct = next((x["pct"] for x in alloc_bucket if x["label"] == "Hybrid"), 0)
    intl_pct = next((x["pct"] for x in alloc_bucket if x["label"] == "International"), 0)
    small_pct = next((x["pct"] for x in alloc_cap if x["label"] == "Small cap"), 0)

    weights = [(h["value"] or h["invested"] or 0) / (value or invested or 1) for h in holdings]
    hhi = sum(w * w for w in weights)
    top = holdings[0] if holdings else None
    top_pct = _pct(top["value"] or top["invested"], value or invested) if top else None

    concentration = min(10, max(1, round(1 + hhi * 12, 1)))
    diversification = min(10, max(1, round(10 - (hhi - 1 / max(len(holdings), 1)) * 18, 1)))
    risk = min(10, max(1, round(1 + equity_pct / 12 + small_pct / 20, 1)))
    liquidity = min(10, max(1, round(3 + debt_pct / 12 + (8 if any("liquid" in (h["name"] + (h["category"] or "")).lower() for h in holdings) else 0), 1)))

    tax_notes = []
    elss = [h for h in holdings if "elss" in (h["name"] + " " + (h["category"] or "")).lower()]
    if elss:
        tax_notes.append(f"{len(elss)} ELSS scheme(s) found — Section 80C lock-in of 3 years may still apply on recent SIPs.")
    regular = [h for h in holdings if "regular" in h["name"].lower() and "direct" not in h["name"].lower()]
    if regular:
        tax_notes.append(f"{len(regular)} Regular-plan name(s) detected. Direct plans usually have a lower expense ratio for the same portfolio.")
    if not tax_notes:
        tax_notes.append("No ELSS or Regular-plan markers were obvious in the names. Tax lots, holding period, and LTCG/STCG need the transaction sheet to be exact.")
    tax_notes.append("Equity-oriented funds: LTCG over ₹1.25 lakh at 12.5% after 12 months (post 23 Jul 2024 rules). Debt funds bought after 1 Apr 2023 are taxed at slab. Confirm with a tax adviser.")

    performers = [h for h in holdings if h.get("ret_pct") is not None]
    best = sorted(performers, key=lambda h: h["ret_pct"], reverse=True)[:5]
    worst = sorted(performers, key=lambda h: h["ret_pct"])[:5]

    overlap = []
    tokens = []
    for h in holdings:
        words = {w for w in re.findall(r"[a-z]+", h["name"].lower()) if len(w) > 3} - {
            "fund", "direct", "growth", "plan", "regular", "india", "indian"
        }
        tokens.append((h, words))
    for i, (a, wa) in enumerate(tokens):
        for b, wb in tokens[i + 1:]:
            if a["bucket"] != b["bucket"]:
                continue
            shared = wa & wb
            if len(shared) >= 2 and a["cap"] == b["cap"]:
                overlap.append({
                    "a": a["name"],
                    "b": b["name"],
                    "reason": f"Same {a['bucket'].lower()} / {a['cap'].lower()} sleeve; shared words: {', '.join(sorted(shared)[:6])}.",
                })

    missing = []
    if debt_pct < 10 and equity_pct > 70:
        missing.append("Little or no dedicated debt / liquid sleeve — liquidity and crash buffer look thin.")
    if intl_pct < 5:
        missing.append("International equity is missing or tiny — rupee and India-factor risk are concentrated.")
    if small_pct > 25:
        missing.append("Small-cap weight is high versus a typical core portfolio.")
    if len(holdings) > 12:
        missing.append(f"{len(holdings)} schemes is usually more than needed; overlap often substitutes for diversification.")
    if len(holdings) < 3 and value:
        missing.append("Very few schemes — manager and style risk is concentrated.")

    actions = []
    if top and top_pct and top_pct >= 25:
        actions.append(f"Cap {top['name']} (about {top_pct}% of the book). Trim or divert SIPs until it is under 20%.")
    if overlap:
        actions.append("Consolidate overlapping same-category funds listed in the overlap table.")
    if regular:
        actions.append("Switch Regular to Direct of the same scheme (off-market / same AMC) after checking exit load and tax.")
    if small_pct > 25:
        actions.append("Reduce small-cap SIP until that sleeve is closer to 10–20% of equity.")
    if debt_pct < 10 and equity_pct > 70:
        actions.append("Add a liquid or short-duration fund as a 6–12 month expense buffer; do not treat equity as emergency money.")
    if sip_monthly and equity_pct > 80:
        actions.append("Keep SIPs, but split new money toward the missing sleeve (debt or international) rather than adding a 13th equity fund.")
    if not actions:
        actions.append("Keep SIPs running; rebalance once a year toward your written equity/debt split.")

    strengths = []
    if sip_monthly:
        strengths.append(f"SIPs of about ₹{sip_monthly:,.0f} a month — rupee-cost averaging is in place.")
    if len(holdings) >= 4 and diversification >= 6:
        strengths.append("More than a handful of sleeves; HHI does not show a single-fund book.")
    if any(h.get("peer_ai") and h["peer_ai"] >= 0.55 for h in holdings):
        strengths.append("Some names also rank well on PrasannaTrade’s local fund AI (AMFI/mfapi, not a SEBI rating).")
    if elss:
        strengths.append("ELSS present — 80C and equity exposure are combined.")
    if not strengths:
        strengths.append("Holdings could be read from the file — that is enough to start a clean-up.")

    weaknesses = []
    if portfolio_xirr is None:
        weaknesses.append("No usable XIRR in the file and dates were incomplete.")
    if overlap:
        weaknesses.append("Same-style funds appear more than once.")
    if intl_pct < 5:
        weaknesses.append("Home-country bias: almost no international sleeve.")
    if regular:
        weaknesses.append("Regular plans raise the drag versus Direct.")
    if small_pct > 25:
        weaknesses.append("Small-cap risk can dominate drawdowns.")
    if not weaknesses:
        weaknesses.append("Main gap is missing history (NAVs over time) for a full drawdown study.")

    # Projections
    mix = equity_pct / 100 * 0.12 + hybrid_pct / 100 * 0.09 + debt_pct / 100 * 0.06 + max(0, 100 - equity_pct - hybrid_pct - debt_pct) / 100 * 0.08
    scenarios = {
        "conservative": round(max(5.0, mix - 3), 1),
        "moderate": round(mix, 1),
        "aggressive": round(min(16.0, mix + 3), 1),
    }
    years = (3, 5, 10, 15)
    projections = []
    for label, cagr in scenarios.items():
        row = {"scenario": label, "cagr": cagr, "paths": []}
        for y in years:
            fv = value * ((1 + cagr / 100) ** y) if value else 0
            sip_fv = 0
            if sip_monthly:
                r = cagr / 100 / 12
                n = y * 12
                sip_fv = sip_monthly * (((1 + r) ** n - 1) / r) * (1 + r) if r else sip_monthly * n
            step = sip_monthly * 0.10
            sip_step = 0
            if sip_monthly:
                sip_step = sip_fv * (1 + 0.045 * y / 5)
            row["paths"].append({
                "years": y,
                "corpus": round(fv + sip_fv, 0),
                "corpus_step_sip": round(fv + sip_step, 0),
                "real_8pct_infl": round((fv + sip_fv) / ((1.06) ** y), 0),
            })
        projections.append(row)
    assumptions.append(
        f"Forward CAGRs are blended from today’s sleeve mix (equity-like {equity_pct:.0f}%, hybrid {hybrid_pct:.0f}%, debt {debt_pct:.0f}%). "
        f"Conservative {scenarios['conservative']}%, moderate {scenarios['moderate']}%, aggressive {scenarios['aggressive']}%. "
        "Inflation in the real column is 6%. This is not a guarantee."
    )

    rating = round(
        min(10, max(3,
            5.5
            + (0.4 if sip_monthly else -0.3)
            + (0.4 if diversification >= 6 else -0.3)
            + (-0.5 if overlap else 0.2)
            + (-0.4 if regular else 0.2)
            + (-0.4 if small_pct > 25 else 0)
            + (0.3 if debt_pct >= 10 else -0.2)
        )),
        1,
    )
    wealth = min(10, max(3, round(5 + equity_pct / 25 + (1 if sip_monthly else 0) - small_pct / 40, 1)))
    stability = min(10, max(2, round(3 + debt_pct / 10 + hybrid_pct / 20 - small_pct / 20, 1)))
    risk_adj = min(10, max(2, round((rating + (10 - risk) + diversification) / 3, 1)))
    tax_score = min(10, max(3, round(7 - (1.2 if regular else 0) + (0.4 if elss else 0), 1)))

    advice = []
    for h in holdings[:8]:
        verb = "Hold"
        why = "Core weight looks usable until a better Direct / lower-overlap option is lined up."
        if h["mode"] == "SIP" and h["bucket"] == "Equity" and overlap and any(h["name"] in (o["a"], o["b"]) for o in overlap):
            verb, why = "Reduce / stop SIP", "Overlaps another fund in the same sleeve. Keep one, divert SIP."
        if "regular" in h["name"].lower() and "direct" not in h["name"].lower():
            verb, why = "Switch to Direct", "Same strategy, lower expense ratio; check exit load and tax."
        if h["cap"] == "Small cap" and small_pct > 25:
            verb, why = "Reduce", "Small-cap sleeve is heavy at the portfolio level."
        if h["bucket"] == "Debt" and debt_pct < 15:
            verb, why = "Increase", "This is the scarce defensive sleeve."
        advice.append({"name": h["name"], "action": verb, "why": why, "value": h["value"], "ret_pct": h["ret_pct"], "alt": None})

    conclusion = (
        f"The file shows {len(holdings)} schemes, about ₹{invested:,.0f} invested and ₹{value:,.0f} now. "
        f"Equity-like exposure is roughly {equity_pct:.0f}%. "
        + (
            "SIPs are doing the heavy lifting — the main job is fewer, cleaner sleeves and a real crash buffer, not more funds. "
            if sip_monthly else
            "There is little SIP signal in the file — either add a standing SIP or confirm the sheet is holdings-only. "
        )
        + "This page is a local reading of your spreadsheet, not regulated investment advice."
    )

    # ==========================================
    # TAX LOSS HARVESTING ENGINE
    # ==========================================
    harvest_candidates = []
    
    for h in holdings:
        if h.get("value") is not None and h.get("invested") is not None:
            gain = h["value"] - h["invested"]
            if gain < 0: # We found a loss
                loss_amt = abs(gain)
                first_date_str = h.get("first_date")
                holding_years = None
                
                if first_date_str:
                    try:
                        first_date = date.fromisoformat(first_date_str)
                        holding_years = (today - first_date).days / 365.25
                    except ValueError:
                        pass
                
                bucket = (h.get("bucket") or "").lower()
                is_equity = any(x in bucket for x in ("equity", "hybrid", "index", "elss"))
                
                if is_equity:
                    # Equity MF Rules (Holding > 12 months = LTCG, <= 12 months = STCG)
                    if holding_years is not None and holding_years >= 1:
                        tax_type = "LTCG"
                        action = f"Book ₹{loss_amt:,.0f} LTCG loss. Set off against other LTCG or carry forward 8 years."
                    else:
                        tax_type = "STCG"
                        action = f"Book ₹{loss_amt:,.0f} STCG loss. Set off against ANY capital gains (STCG or LTCG) this FY."
                else:
                    # Debt MF Rules (Post Apr 2023, taxed at slab rate)
                    tax_type = "STCG/Slab"
                    action = f"Book ₹{loss_amt:,.0f} loss. Reduces your taxable income or STCG for this FY."
                
                harvest_candidates.append({
                    "name": h["name"],
                    "loss": round(loss_amt, 2),
                    "tax_type": tax_type,
                    "action": action,
                    "bucket": h.get("bucket")
                })
                
    # Sort by highest loss first (biggest tax benefit)
    harvest_candidates.sort(key=lambda x: x["loss"], reverse=True)

    peer = compare_to_peers(holdings, catalog)
    if peer.get("compared"):
        assumptions.append(
            f"Matched {peer['compared']} holding(s) to AMFI Direct Growth peers for same-group rank."
        )
    else:
        assumptions.append("Could not match holdings to AMFI names — peer compare is thin. Refresh NAVs on Mutual funds, then analyse again.")

    report = {
        "disclaimer": (
            "Analysis of the uploaded spreadsheet using Indian mutual-fund context. "
            "Not SEBI-registered advice. Confirm tax and switches with a registered adviser."
        ),
        "file": filename,
        "sheet": sheet_name,
        "columns": mapping,
        "sheets": sheets_meta,
        "assumptions": assumptions,
        "summary": {
            "funds": len(holdings),
            "invested": _inr(invested),
            "value": _inr(value),
            "gain": _inr(gain),
            "ret_pct": ret_pct,
            "xirr": portfolio_xirr,
            "sip_monthly": _inr(sip_monthly) or 0,
            "sip_value": _inr(sip_value) or 0,
            "lump_value": _inr(lump_value) or 0,
            "unknown_value": _inr(unknown_value) or 0,
            "equity_pct": equity_pct,
            "debt_pct": debt_pct,
            "hybrid_pct": hybrid_pct,
            "intl_pct": intl_pct,
            "small_pct": small_pct,
            "risk": risk,
            "diversification": diversification,
            "concentration": concentration,
            "liquidity": liquidity,
        },
        "allocation": {
            "bucket": alloc_bucket,
            "cap": alloc_cap,
            "amc": alloc_amc[:8],
        },
        "tax": tax_notes,
        "holdings": [{
            "name": h["name"],
            "amc": h.get("amc"),
            "category": h.get("category"),
            "bucket": h["bucket"],
            "cap": h["cap"],
            "mode": h["mode"],
            "sip": h["sip"],
            "units": h["units"],
            "invested": h["invested"],
            "value": h["value"],
            "gain": h["gain"],
            "ret_pct": h["ret_pct"],
            "xirr": h.get("xirr"),
            "first_date": h.get("first_date"),
            "peer_1y": h.get("peer_1y"),
            "peer_3y": h.get("peer_3y"),
            "peer_ai": h.get("peer_ai"),
            "amfi_code": h.get("amfi_code"),
            "amfi_name": h.get("amfi_name"),
        } for h in holdings],
        "peer": peer,
        "performance": {
            "best": [{"name": h["name"], "ret_pct": h["ret_pct"], "gain": h["gain"]} for h in best],
            "worst": [{"name": h["name"], "ret_pct": h["ret_pct"], "gain": h["gain"]} for h in worst],
            "benchmarks": [
                {"label": "Nifty 50", "note": "Long-run ~12% nominal is a common planning yardstick, not a promise."},
                {"label": "Sensex", "note": "Tracks large-cap India; similar to Nifty 50 over long windows."},
                {"label": "Nifty Midcap 150 / Smallcap 250", "note": "Higher return and deeper drawdowns than Nifty 50."},
                {"label": "Inflation (CPI)", "note": "Plan with 5–6%. Real wealth is nominal return minus this."},
            ],
            "history_limit": (
                "The upload is a snapshot (and optional lots). Full path returns, max drawdown, and SIP-timing "
                "need a transaction export with every debit/credit. Until then, best/worst are file-based absolute returns."
            ),
        },
        "health": {
            "allocation_view": (
                f"Equity-like {equity_pct:.0f}%, hybrid {hybrid_pct:.0f}%, debt {debt_pct:.0f}%, international {intl_pct:.0f}%. "
                + (
                    "Aggressive for someone who still needs money in under five years."
                    if equity_pct >= 80 else
                    "A usable growth mix if the horizon is 7+ years and there is a separate emergency fund."
                    if equity_pct >= 55 else
                    "Conservative on equity — growth will track debt and hybrid more than Nifty."
                )
            ),
            "overlap": overlap[:12],
            "missing": missing,
            "risk_notes": [
                f"Volatility / beta: equity-like {equity_pct:.0f}% — expect Nifty-like swings, worse if small-cap is {small_pct:.0f}%.",
                "Debt interest-rate and credit risk apply only to the debt sleeve; duration is unknown without scheme factsheets.",
                "Liquidity: open-ended equity usually T+2/T+3; ELSS is locked 3 years from each SIP.",
            ],
        },
        "projections": {
            "assumptions": scenarios,
            "inflation": 6,
            "rows": projections,
        },
        "advice": advice,
        "tax_harvest": harvest_candidates,  # <-- NEW: Tax Loss Harvesting Data
        "benchmarking": {
            "retail": "A common Indian SIP book is 4–8 equity funds plus optional ELSS. More than 12 is usually over-engineered.",
            "aggressive": "Aggressive books run 80–90% equity with a small liquid sleeve. That matches only if the horizon is long.",
            "conservative": "Conservative books keep 40%+ debt/hybrid. This file is not that if equity-like is high.",
            "pro": "A clean book is 1–2 flexi/large, 1 mid or small, 1 international, 1 short-duration/liquid, optional ELSS.",
            "quality": "Above average if SIPs exist and overlap is low; below average if Regular plans and 12+ lookalike schemes stack up.",
        },
        "verdict": {
            "rating": rating,
            "wealth": wealth,
            "stability": stability,
            "risk_adj": risk_adj,
            "tax": tax_score,
            "diversification": diversification,
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "actions": actions[:5],
            "conclusion": conclusion,
        },
    }
    return apply_peer_advice(report)