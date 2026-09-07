"""
Indian mutual fund NAVs from AMFI's public daily file. No API key.

    https://www.amfiindia.com/spages/NAVAll.txt

Optional 1Y / 3Y / 5Y returns from mfapi.in (also free), cached locally.
"""
from __future__ import annotations

import csv
import glob
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import requests

from fund_scorer import annotate_rows, attach_peer_metrics, score_fund, summarize_ai
from utils import get_logger, get_path

log = get_logger("funds")

AMFI_NAV_URLS = (
    "https://portal.amfiindia.com/spages/NAVAll.txt",
    "https://www.amfiindia.com/spages/NAVAll.txt",
)
MFAPI_URL = "https://api.mfapi.in/mf/{code}"

CAT_RE = re.compile(
    r"^(Open Ended|Close Ended|Interval Fund)\s*Schemes?\s*\((.+)\)$",
    re.I,
)
HEADER_PREFIX = "scheme code"

_lock = threading.Lock()
_returns_lock = threading.Lock()
_memory: dict | None = None
_warm_started = False
_RETURN_KEYS = ("ret_1m", "ret_6m", "ret_1y", "ret_3y", "ret_5y", "vol_1y", "max_dd_1y", "sharpe_1y")


def _cache_dir() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mutual_funds")
    os.makedirs(path, exist_ok=True)
    return path


def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/plain,*/*",
    }


def _http_session(*, use_env_proxy: bool = False) -> requests.Session:
    """Corporate HTTP(S)_PROXY often returns 403 for AMFI. Prefer a direct connection."""
    session = requests.Session()
    session.trust_env = use_env_proxy
    session.headers.update(_headers())
    return session


def _bucket_for(inner: str) -> str:
    text = inner.lower()
    if "index" in text or "etf" in text:
        return "Index"
    head = text.split("-", 1)[0]
    if "equity" in head:
        return "Equity"
    if "debt" in head:
        return "Debt"
    if "hybrid" in head:
        return "Hybrid"
    if "solution" in head:
        return "Solution"
    return "Other"


def _short_category(inner: str) -> str:
    if "-" in inner:
        return inner.split("-", 1)[1].strip()
    return inner.strip()


def cap_band(name: str, category: str = "") -> str:
    """Large / mid / small from AMFI category + scheme name. Large & mid first so it is not tagged as mid."""
    text = f"{name} {category}".lower()
    if "large & mid" in text or "large and mid" in text or "large&mid" in text:
        return "Large & mid"
    if "small" in text:
        return "Small cap"
    if "mid" in text:
        return "Mid cap"
    if "flexi" in text or "multi cap" in text or "multicap" in text:
        return "Flexi / multi"
    if "large" in text or "bluechip" in text or "blue chip" in text:
        return "Large cap"
    if "nifty 50" in text or "nifty50" in text or "sensex" in text:
        return "Large cap"
    return "Other sleeve"


def _attach_cap(rows: list[dict]):
    for row in rows:
        row["cap"] = cap_band(row.get("name") or "", row.get("category") or "")


def _plan_for(name: str) -> str:
    return "Direct" if "direct" in name.lower() else "Regular"


def _option_for(name: str) -> str:
    n = name.lower()
    if "growth" in n:
        return "Growth"
    if "idcw" in n or "dividend" in n or "income dist" in n:
        return "IDCW"
    if "bonus" in n:
        return "Bonus"
    return "Other"


def _parse_nav_date(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_navall(text: str) -> list[dict]:
    """Parse AMFI NAVAll.txt. Column layout changed in 2026: Plan/Option sit
    before NAV, so NAV is always the second-last field and date the last."""
    rows = []
    scheme_type = ""
    category_inner = ""
    amc = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.lower().startswith(HEADER_PREFIX):
            continue
        cat = CAT_RE.match(line)
        if cat:
            kind = cat.group(1).lower()
            if "open" in kind:
                scheme_type = "Open Ended"
            elif "close" in kind:
                scheme_type = "Close Ended"
            else:
                scheme_type = "Interval"
            category_inner = cat.group(2).strip()
            amc = ""
            continue
        if ";" not in line:
            amc = line
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        nav_raw = parts[-2].replace(",", "")
        try:
            nav = float(nav_raw)
        except ValueError:
            continue
        name = parts[3] if len(parts) >= 8 else parts[3]
        plan_col = parts[4] if len(parts) >= 8 else ""
        option_col = parts[5] if len(parts) >= 8 else ""
        if plan_col and plan_col.lower() not in name.lower():
            name = f"{name} — {plan_col}"
        nav_date = _parse_nav_date(parts[-1])
        inner = category_inner or "Uncategorised"
        rows.append({
            "code": parts[0],
            "name": name,
            "amc": amc,
            "scheme_type": scheme_type or "Open Ended",
            "category": _short_category(inner),
            "bucket": _bucket_for(inner),
            "cap": cap_band(name, _short_category(inner)),
            "plan": _plan_for(f"{plan_col} {name}"),
            "option": _option_for(f"{option_col} {name}"),
            "nav": round(nav, 4),
            "nav_date": nav_date,
            "isin": parts[1] if parts[1] not in ("", "-") else (parts[2] if len(parts) > 2 and parts[2] not in ("", "-") else None),
        })
    return rows


def _csv_path(iso_date: str) -> str:
    return get_path(f"data/mutual_funds/nav_{iso_date}.csv")


def _returns_path() -> str:
    return get_path("data/mutual_funds/returns.json")


def _save_csv(iso_date: str, rows: list[dict]):
    path = _csv_path(iso_date)
    fields = ["code", "name", "amc", "scheme_type", "category", "bucket", "plan", "option", "nav", "nav_date", "isin"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                row["nav"] = float(row["nav"])
            except (TypeError, ValueError):
                continue
            rows.append(row)
    _attach_cap(rows)
    return rows


def _dated_caches() -> list[str]:
    files = glob.glob(os.path.join(_cache_dir(), "nav_*.csv"))
    files.sort(reverse=True)
    return files


def _nav_map(rows: list[dict]) -> dict[str, float]:
    return {r["code"]: r["nav"] for r in rows if r.get("nav") is not None}


def _attach_change(rows: list[dict], prev_rows: list[dict] | None):
    prev = _nav_map(prev_rows or [])
    cache = _load_returns_cache()
    for row in rows:
        old = prev.get(row["code"])
        if old and old > 0:
            row["chg_pct"] = round((row["nav"] / old - 1) * 100, 2)
            row["prev_nav"] = old
        else:
            row["chg_pct"] = None
            row["prev_nav"] = None
        extra = cache.get(row["code"])
        if isinstance(extra, dict):
            for key in _RETURN_KEYS:
                if extra.get(key) is not None:
                    row[key] = extra[key]
    annotate_rows(rows)


def merge_cached_returns(rows: list[dict]) -> int:
    """Apply any local mfapi cache onto in-memory rows (including stale days)."""
    cache = _load_returns_cache()
    filled = 0
    for row in rows:
        extra = cache.get(row.get("code"))
        if not isinstance(extra, dict):
            continue
        before = row.get("ret_1y")
        for key in _RETURN_KEYS:
            if extra.get(key) is not None:
                row[key] = extra[key]
        if before is None and row.get("ret_1y") is not None:
            filled += 1
    if filled:
        annotate_rows(rows)
    return filled


def _fetch_amfi() -> str:
    last_error = None
    # Try direct first so a broken HTTP_PROXY/HTTPS_PROXY cannot block AMFI.
    for use_proxy in (False, True):
        session = _http_session(use_env_proxy=use_proxy)
        for url in AMFI_NAV_URLS:
            try:
                resp = session.get(url, timeout=30, allow_redirects=True)
                resp.raise_for_status()
                text = resp.text
                if "Scheme Code" not in text[:400]:
                    last_error = ValueError(f"{url} did not look like NAVAll.txt")
                    continue
                return text
            except Exception as exc:
                last_error = exc
                via = "proxy" if use_proxy else "direct"
                log.warning(f"AMFI fetch failed from {url} ({via}): {exc}")
    raise last_error or ValueError("AMFI NAV file could not be downloaded")


def _payload_from_rows(rows: list[dict], as_of: str | None, cached: bool) -> dict:
    _attach_cap(rows)
    buckets = {}
    caps = {}
    for row in rows:
        buckets[row["bucket"]] = buckets.get(row["bucket"], 0) + 1
        caps[row.get("cap") or "Other sleeve"] = caps.get(row.get("cap") or "Other sleeve", 0) + 1
    nav_dates = [r["nav_date"] for r in rows if r.get("nav_date")]
    return {
        "as_of": as_of or (max(nav_dates) if nav_dates else None),
        "cached": cached,
        "count": len(rows),
        "amcs": len({r["amc"] for r in rows if r.get("amc")}),
        "buckets": buckets,
        "caps": caps,
        "rows": rows,
        "source": "AMFI NAVAll.txt",
    }


def load_or_fetch(refresh: bool = False) -> dict:
    today = date.today().isoformat()
    today_path = _csv_path(today)
    caches = _dated_caches()
    if not refresh and os.path.exists(today_path):
        rows = _load_csv(today_path)
        prev_path = next((p for p in caches if os.path.basename(p) != os.path.basename(today_path)), None)
        _attach_change(rows, _load_csv(prev_path) if prev_path else None)
        log.info(f"Loaded {len(rows)} funds from today's AMFI cache")
        return _payload_from_rows(rows, None, True)

    log.info("Downloading AMFI NAVAll.txt")
    try:
        rows = parse_navall(_fetch_amfi())
    except Exception as exc:
        if caches:
            log.warning(f"AMFI download failed ({exc}); using last cache")
            latest = caches[0]
            rows = _load_csv(latest)
            prev_path = caches[1] if len(caches) > 1 else None
            _attach_change(rows, _load_csv(prev_path) if prev_path else None)
            stamp = os.path.basename(latest).replace("nav_", "").replace(".csv", "")
            return _payload_from_rows(rows, stamp, True)
        log.warning(f"AMFI download failed ({exc}); continuing without fund catalog")
        return _payload_from_rows([], None, True)
    if not rows:
        if caches:
            log.warning("AMFI parsed to zero schemes; using last cache")
            latest = caches[0]
            rows = _load_csv(latest)
            prev_path = caches[1] if len(caches) > 1 else None
            _attach_change(rows, _load_csv(prev_path) if prev_path else None)
            stamp = os.path.basename(latest).replace("nav_", "").replace(".csv", "")
            return _payload_from_rows(rows, stamp, True)
        log.warning("AMFI parsed to zero schemes; continuing without fund catalog")
        return _payload_from_rows([], None, True)
    nav_dates = [r["nav_date"] for r in rows if r.get("nav_date")]
    as_of = max(nav_dates) if nav_dates else today
    _save_csv(today, rows)
    prev_path = next((p for p in _dated_caches() if not p.endswith(f"nav_{today}.csv")), None)
    _attach_change(rows, _load_csv(prev_path) if prev_path else None)
    log.info(f"Parsed {len(rows)} schemes, NAV date {as_of}")
    return _payload_from_rows(rows, as_of, False)


def get_funds(refresh: bool = False) -> dict:
    global _memory
    try:
        with _lock:
            if _memory is not None and not refresh:
                rows = _memory.get("rows") or []
                merge_cached_returns(rows)
                if rows and rows[0].get("ai_score") is None:
                    annotate_rows(rows)
                payload = _memory
            else:
                _memory = load_or_fetch(refresh)
                merge_cached_returns(_memory.get("rows") or [])
                payload = _memory
        schedule_warm()
        return payload
    except Exception as exc:
        log.warning(f"AMFI catalog unavailable: {exc}")
        return _payload_from_rows([], None, True)


def _load_returns_cache() -> dict:
    path = _returns_path()
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_returns_cache(cache: dict):
    with open(_returns_path(), "w") as f:
        json.dump(cache, f)


def _nav_on_or_before(points: list[tuple[date, float]], target: date) -> float | None:
    chosen = None
    for d, nav in points:
        if d <= target:
            chosen = nav
            break
    return chosen


def _pct(now: float, then: float | None, years: float | None = None) -> float | None:
    if not then or then <= 0 or now <= 0:
        return None
    simple = now / then
    if years and years >= 1:
        return round((simple ** (1 / years) - 1) * 100, 2)
    return round((simple - 1) * 100, 2)


def _returns_from_history(payload: dict) -> dict | None:
    series = payload.get("data") or []
    points = []
    for item in series:
        try:
            d = datetime.strptime(item["date"], "%d-%m-%Y").date()
            nav = float(item["nav"])
        except (KeyError, TypeError, ValueError):
            continue
        points.append((d, nav))
    if len(points) < 2:
        return None
    points.sort(key=lambda x: x[0], reverse=True)
    latest_d, latest_n = points[0]
    chrono = list(reversed(points))
    year_pts = [(d, n) for d, n in chrono if d >= latest_d - timedelta(days=365)]
    year_navs = [n for _, n in year_pts]
    year_rets = []
    for i in range(1, len(year_navs)):
        if year_navs[i - 1] > 0:
            year_rets.append(year_navs[i] / year_navs[i - 1] - 1)
    vol_1y = None
    if len(year_rets) >= 20:
        vol_1y = round(float(pd_std(year_rets) * (252 ** 0.5) * 100), 2)
    max_dd = None
    if year_navs:
        peak = year_navs[0]
        worst = 0.0
        for nav in year_navs:
            if nav > peak:
                peak = nav
            if peak > 0:
                worst = min(worst, nav / peak - 1)
        max_dd = round(worst * 100, 2)
    ret_1y = _pct(latest_n, _nav_on_or_before(points, latest_d - timedelta(days=365)))
    sharpe_1y = None
    if ret_1y is not None and vol_1y and vol_1y > 0:
        sharpe_1y = round(ret_1y / vol_1y, 2)
    return {
        "ret_1m": _pct(latest_n, _nav_on_or_before(points, latest_d - timedelta(days=30))),
        "ret_6m": _pct(latest_n, _nav_on_or_before(points, latest_d - timedelta(days=182))),
        "ret_1y": ret_1y,
        "ret_3y": _pct(latest_n, _nav_on_or_before(points, latest_d - timedelta(days=365 * 3)), 3),
        "ret_5y": _pct(latest_n, _nav_on_or_before(points, latest_d - timedelta(days=365 * 5)), 5),
        "vol_1y": vol_1y,
        "max_dd_1y": max_dd,
        "sharpe_1y": sharpe_1y,
        "fetched": date.today().isoformat(),
    }


def pd_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return var ** 0.5


def _fetch_one_return(code: str) -> tuple[str, dict | None]:
    try:
        resp = _http_session(use_env_proxy=False).get(
            MFAPI_URL.format(code=code), timeout=12
        )
        resp.raise_for_status()
        parsed = _returns_from_history(resp.json())
        return code, parsed
    except Exception as exc:
        log.warning(f"Returns fetch failed for {code}: {exc}")
        return code, None


def _cache_has_returns(entry) -> bool:
    return isinstance(entry, dict) and (
        entry.get("fetched") or entry.get("ret_1y") is not None or entry.get("ret_3y") is not None
    )


def get_returns(codes: list[str]) -> dict:
    """1Y absolute, 3Y/5Y CAGR. Reuse any cached history; refetch only when missing."""
    codes = [c for c in codes if c][:200]
    with _returns_lock:
        cache = _load_returns_cache()
    missing = [c for c in codes if not _cache_has_returns(cache.get(c))]
    if missing:
        log.info(f"Fetching mfapi history for {len(missing)} schemes")
        fresh = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_fetch_one_return, code) for code in missing]
            for fut in as_completed(futs):
                code, parsed = fut.result()
                fresh[code] = parsed or {"fetched": date.today().isoformat()}
        with _returns_lock:
            cache = _load_returns_cache()
            cache.update(fresh)
            _save_returns_cache(cache)
    out = {c: dict(cache[c]) for c in codes if c in cache}
    with _lock:
        by_code = {r["code"]: r for r in ((_memory or {}).get("rows") or [])}
        for code, extra in out.items():
            row = by_code.get(code)
            if not row:
                continue
            for key in _RETURN_KEYS:
                if extra.get(key) is not None:
                    row[key] = extra[key]
            score_fund(row)
            extra["ai_score"] = row.get("ai_score")
            extra["ai_depth"] = row.get("ai_depth")
            extra["ai_commentary"] = row.get("ai_commentary")
            extra["cat_rank_1y"] = row.get("cat_rank_1y")
            extra["cat_pct_1y"] = row.get("cat_pct_1y")
            extra["cat_n"] = row.get("cat_n")
            extra["quality"] = row.get("quality")
            extra["vol_band"] = row.get("vol_band")
            extra["cat_mean_1y"] = row.get("cat_mean_1y")
            extra["cat_pct_ai"] = row.get("cat_pct_ai")
        attach_peer_metrics((_memory or {}).get("rows") or [])
        for code, extra in out.items():
            row = by_code.get(code)
            if not row:
                continue
            extra["cat_rank_1y"] = row.get("cat_rank_1y")
            extra["cat_pct_1y"] = row.get("cat_pct_1y")
            extra["cat_n"] = row.get("cat_n")
            extra["cat_mean_1y"] = row.get("cat_mean_1y")
            extra["cat_pct_ai"] = row.get("cat_pct_ai")
    return out


def schedule_warm(limit: int = 2500):
    """Fetch 1Y/3Y for Direct Growth names that still lack history."""
    global _warm_started
    with _returns_lock:
        if _warm_started:
            return
        _warm_started = True
    threading.Thread(target=warm_returns, args=(limit,), daemon=True, name="fund-warm").start()


def warm_returns(limit: int = 160):
    rows = ((_memory or {}).get("rows") or [])
    need = []
    seen = set()
    for row in rows:
        code = row.get("code")
        if not code or code in seen:
            continue
        if row.get("scheme_type") and row.get("scheme_type") != "Open Ended":
            continue
        if row.get("plan") != "Direct" or row.get("option") != "Growth":
            continue
        if row.get("ret_1y") is not None:
            continue
        seen.add(code)
        need.append(code)
        if len(need) >= limit:
            break
    if not need:
        return
    log.info(f"Warming mfapi returns for {len(need)} Direct Growth schemes")
    get_returns(need)
