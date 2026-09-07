"""
Rank mutual-fund schemes from AMFI NAVs and optional mfapi history.

This is not the stock GBM / Lorentzian model. Those need OHLCV bars.
The fund score is a 0–1 blend of 1D NAV change and 1Y / 3Y / 5Y returns,
adjusted for category outperformance.
"""
from __future__ import annotations

def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def _unit(value, lo: float, hi: float):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if hi == lo:
        return 0.5
    return _clip((number - lo) / (hi - lo), 0.0, 1.0)

def _pct(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _fmt_pct(value: float | None) -> str | None:
    if value is None:
        return None
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"

def score_fund(row: dict) -> dict:
    """Mutates and returns row with ai_score, ai_depth, ai_commentary."""
    chg = _pct(row.get("chg_pct"))
    r1 = _pct(row.get("ret_1y"))
    r3 = _pct(row.get("ret_3y"))
    r5 = _pct(row.get("ret_5y"))
    pieces = []
    if chg is not None:
        pieces.append((_unit(chg, -2.5, 2.5), 0.18, "1D"))
    if r1 is not None:
        pieces.append((_unit(r1, -18.0, 38.0), 0.30, "1Y"))
    if r3 is not None:
        pieces.append((_unit(r3, -8.0, 24.0), 0.32, "3Y"))
    if r5 is not None:
        pieces.append((_unit(r5, -5.0, 22.0), 0.20, "5Y"))

    if not pieces:
        prior = 0.46 if (row.get("plan") or "") == "Direct" else 0.42
        if (row.get("option") or "") == "Growth":
            prior += 0.02
        row["ai_score"] = round(_clip(prior, 0.0, 1.0), 3)
        row["ai_depth"] = "base"
        bits = [x for x in (row.get("plan"), row.get("option"), row.get("category") or row.get("bucket")) if x]
        row["ai_commentary"] = (
            f"{' · '.join(bits)}. Baseline rank only — no 1D NAV change yet "
            "and no 1Y/3Y history. Refresh NAVs on a second day or wait for returns to load."
        )
        return row

    weight = sum(w for _, w, _ in pieces)
    score = sum(v * w for v, w, _ in pieces) / weight
    if r1 is not None and r3 is not None and r5 is not None:
        if r1 > 0 and r3 > 0 and r5 > 0:
            score += 0.05
        if r1 < -8 and r3 > 10:
            score -= 0.07
    bucket = (row.get("bucket") or "").lower()
    if bucket == "debt" and chg is not None and abs(chg) > 0.8:
        score -= 0.04
    if (row.get("plan") or "") == "Direct":
        score += 0.02
    score = round(_clip(score, 0.0, 1.0), 3)

    has_returns = r1 is not None or r3 is not None or r5 is not None
    depth = "returns" if has_returns else "nav"
    bits = [x for x in (
        row.get("plan"),
        row.get("option"),
        row.get("category") or row.get("bucket"),
        f"1D {_fmt_pct(chg)}" if chg is not None else None,
        f"1Y {_fmt_pct(r1)}" if r1 is not None else None,
        f"3Y {_fmt_pct(r3)} CAGR" if r3 is not None else None,
        f"5Y {_fmt_pct(r5)} CAGR" if r5 is not None else None,
    ) if x]
    if depth == "nav":
        tail = "Score from one-day AMFI NAV only. 1Y/3Y load on this page for a fuller rank."
    else:
        tail = "Score from AMFI NAVs and mfapi history — not the stock GBM model. Not advice."
    row["ai_score"] = score
    row["ai_depth"] = depth
    row["ai_commentary"] = f"{' · '.join(bits)}. {tail}"
    row["quality"] = _fund_quality(chg, r1, r3, r5, row)
    row["vol_band"] = _vol_band(row.get("vol_1y"), row.get("bucket"))
    return row

def _fund_quality(chg, r1, r3, r5, row: dict):
    bits = []
    if r1 is not None:
        bits.append(_unit(r1, -15, 32))
    if r3 is not None:
        bits.append(_unit(r3, -6, 22))
    sharpe = _pct(row.get("sharpe_1y"))
    if sharpe is not None:
        bits.append(_unit(sharpe, -0.4, 1.6))
    dd = _pct(row.get("max_dd_1y"))
    if dd is not None:
        bits.append(_unit(-dd, 0, 25))
    if r1 is not None and r3 is not None and r5 is not None:
        bits.append(0.85 if r1 > 0 and r3 > 0 and r5 > 0 else 0.35)
    if (row.get("plan") or "") == "Direct":
        bits.append(0.7)
    if not bits:
        return None
    return round(sum(bits) / len(bits), 3)

def _vol_band(vol, bucket: str | None) -> str | None:
    vol = _pct(vol)
    if vol is None:
        return None
    head = (bucket or "").lower()
    if head == "debt":
        if vol < 2:
            return "Calm"
        if vol < 5:
            return "Typical"
        return "Jumpy"
    if vol < 12:
        return "Calm"
    if vol < 22:
        return "Typical"
    return "Jumpy"

def attach_peer_metrics(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list] = {}
    for row in rows:
        if row.get("scheme_type") and row["scheme_type"] != "Open Ended":
            continue
        key = (row.get("category") or row.get("bucket") or "Other", row.get("plan") or "", row.get("option") or "")
        groups.setdefault(key, []).append(row)
    
    for peers in groups.values():
        n = len(peers)
        with_ret = [p for p in peers if _pct(p.get("ret_1y")) is not None]
        with_ret.sort(key=lambda p: float(p["ret_1y"]), reverse=True)
        mean = None
        if with_ret:
            mean = round(sum(float(p["ret_1y"]) for p in with_ret) / len(with_ret), 2)
        n_ret = len(with_ret)
        
        for i, peer in enumerate(with_ret):
            peer["cat_n"] = n
            peer["cat_rank_1y"] = i + 1
            peer["cat_pct_1y"] = round((n_ret - i) / n_ret * 100, 1) if n_ret else None
            peer["cat_mean_1y"] = mean
            
            # --- NEW: CONTEXT-AWARE SCORING ---
            # Adjust AI score based on category percentile to prevent recommending absolute-return laggards
            if n_ret >= 5: 
                percentile = (n_ret - i) / n_ret
                base_score = float(peer.get("ai_score") or 0.5)
                
                if percentile >= 0.80: # Top 20% of category
                    peer["ai_score"] = round(min(1.0, base_score + 0.05), 3)
                    peer["cat_verdict"] = "Category Leader"
                elif percentile <= 0.30: # Bottom 30% of category
                    peer["ai_score"] = round(max(0.0, base_score - 0.05), 3)
                    peer["cat_verdict"] = "Category Laggard"
                else:
                    peer["cat_verdict"] = "Average"
                    
                # Also adjust the "Quality" metric used in peer comparisons
                if peer.get("quality"):
                    quality_adj = 0.1 if percentile >= 0.8 else (-0.1 if percentile <= 0.3 else 0)
                    peer["quality"] = round(peer["quality"] + quality_adj, 3)

        scored = [p for p in peers if p.get("ai_score") is not None]
        scored.sort(key=lambda p: float(p["ai_score"]), reverse=True)
        n_ai = len(scored)
        for i, peer in enumerate(scored):
            peer["cat_n"] = n
            peer["cat_rank_ai"] = i + 1
            peer["cat_pct_ai"] = round((n_ai - i) / n_ai * 100, 1) if n_ai else None
            if "cat_mean_1y" not in peer:
                peer["cat_mean_1y"] = mean
    return rows

def annotate_rows(rows: list[dict]) -> list[dict]:
    for row in rows:
        score_fund(row)
    attach_peer_metrics(rows)
    return rows

def summarize_ai(rows: list[dict]) -> dict:
    scored = [r for r in rows if r.get("ai_score") is not None]
    scores = [float(r["ai_score"]) for r in scored]
    high = [r for r in scored if float(r["ai_score"]) >= 0.52]
    by_bucket = {}
    for row in high:
        bucket = row.get("bucket") or "Other"
        by_bucket[bucket] = by_bucket.get(bucket, 0) + 1
    return {
        "scored": len(scored),
        "high": len(high),
        "full": sum(1 for r in scored if r.get("ai_depth") == "returns"),
        "nav_only": sum(1 for r in scored if r.get("ai_depth") == "nav"),
        "mean": round(sum(scores) / len(scores), 3) if scores else None,
        "high_by_bucket": by_bucket,
    }