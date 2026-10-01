import re
import calendar
import difflib

LABELS = {
    "in": "intime",
    "out": "outtime",
    "total": "totalduration",
    "shift": "shiftcode",
    "late": "lateby",
    "early": "earlyby",
    "perm": "permissiontime",
    "half": "halfcl",
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def match_label(text):
    """Return one of LABELS keys (in/out/total/...) or None."""
    n = norm(text)
    if not n:
        return None
    best = difflib.get_close_matches(n, list(LABELS.values()), n=1, cutoff=0.78)
    if best:
        for k, v in LABELS.items():
            if v == best[0]:
                return k
    return None

def hms_to_sec(v):
    """'9:55:03' / '09:55' / '-' -> seconds (None if blank)."""
    v = (v or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", v)
    if not m:
        return None
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)


def sec_to_hms(s):
    s = int(max(0, s or 0))
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


_TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", re.I)


def parse_shift(text):
    """-> dict(code, start_sec, end_sec, label)"""
    text = (text or "").strip()
    out = {"code": "", "start": None, "end": None, "label": text}
    if not text or set(text) <= {"-"}:
        return out
    m = re.match(r"^\s*([A-Za-z]{1,3}\d*?)(?=(?i:shift)|\s|$)", text)
    if m:
        out["code"] = m.group(1).upper()
    times = []
    for h, mi, ap in _TIME_RE.findall(text):
        h = int(h) % 12 + (12 if ap.lower() == "pm" else 0)
        times.append(h * 3600 + int(mi or 0) * 60)
    if len(times) >= 2:
        out["start"], out["end"] = times[0], times[1]

        def f(t):
            h, mi = t // 3600, (t % 3600) // 60
            ap = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            return f"{h12}{':%02d' % mi if mi else ''} {ap}"

        out["label"] = f"{out['code']}  {f(times[0])} - {f(times[1])}"
    return out

_WD = {n.lower(): i for i, n in enumerate(calendar.day_name)}
_WD.update({n.lower(): i for i, n in enumerate(calendar.day_abbr)})
_ORD = {"1st": 1, "first": 1, "2nd": 2, "second": 2, "3rd": 3, "third": 3,
        "4th": 4, "fourth": 4, "5th": 5, "fifth": 5, "last": -1}
_MON = {}
for i in range(1, 13):
    _MON[calendar.month_name[i].lower()] = i
    _MON[calendar.month_abbr[i].lower()] = i
_MON["sept"] = 9
def parse_days_text(text, year, month):
    """Return sorted list of day numbers (1..N) of the given month."""
    n = calendar.monthrange(year, month)[1]
    t = (text or "").lower()
    days = set()
    wd_pat = r"(" + "|".join(sorted(_WD, key=len, reverse=True)) + r")s?\b"
    ord_pat = r"(1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth|last)"
    ordwd = rf"((?:{ord_pat}(?:\s*(?:,|and|&)\s*)?)+)\s*{wd_pat}"
    for m in re.finditer(ordwd, t):
        ords = [_ORD[o] for o in re.findall(ord_pat, m.group(1))]
        wd = _WD[m.group(m.lastindex)]
        cols = [d for d in range(1, n + 1) if calendar.weekday(year, month, d) == wd]
        for o in ords:
            try:
                days.add(cols[o - 1] if o > 0 else cols[-1])
            except IndexError:
                pass
    for m in re.finditer(rf"\b(?:every|all|each)\s+{wd_pat}", t):
        wd = _WD[m.group(1)]
        days.update(d for d in range(1, n + 1) if calendar.weekday(year, month, d) == wd)
    t = re.sub(ordwd, " ", t)
    t = re.sub(rf"\b(?:every|all|each)\s+{wd_pat}", " ", t)
    def full(m):
        d, mo = int(m.group(1)), int(m.group(2))
        y = m.group(3)
        y = (2000 + int(y)) if y and len(y) == 2 else (int(y) if y else year)
        if mo == month and y == year and 1 <= d <= n:
            days.add(d)
        return " "
    t = re.sub(r"\b(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?\b", full, t)
    def with_month(pattern, order):
        nonlocal t
        for m in list(re.finditer(pattern, t)):
            mon = _MON[m.group(order["m"])]
            if mon != month:
                continue
            a = int(m.group(order["a"]))
            b = int(m.group(order["b"])) if order.get("b") and m.group(order["b"]) else a
            for d in range(min(a, b), max(a, b) + 1):
                if 1 <= d <= n:
                    days.add(d)
        t = re.sub(pattern, " ", t)

    mon_re = "|".join(sorted(_MON, key=len, reverse=True))
    with_month(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*(?:-|to|till|through)\s*(\d{{1,2}})(?:st|nd|rd|th)?)?\s*({mon_re})\b",
               {"a": 1, "b": 2, "m": 3})
    with_month(rf"\b({mon_re})\s*(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*(?:-|to|till|through)\s*(\d{{1,2}})(?:st|nd|rd|th)?)?\b",
               {"m": 1, "a": 2, "b": 3})
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|to|till|through)\s*(\d{1,2})(?:st|nd|rd|th)?\b", t):
        a, b = int(m.group(1)), int(m.group(2))
        for d in range(min(a, b), max(a, b) + 1):
            if 1 <= d <= n:
                days.add(d)
    t = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:-|to|till|through)\s*(\d{1,2})(?:st|nd|rd|th)?\b", " ", t)
    for m in re.finditer(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", t):
        d = int(m.group(1))
        if 1 <= d <= n:
            days.add(d)
    return sorted(days)
