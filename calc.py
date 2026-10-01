import calendar
from nlp_utils import hms_to_sec, sec_to_hms, parse_shift

SUN, HOL, PRESENT, LEAVE = "sunday", "holiday", "present", "leave"


def calculate(data, sundays, holidays, cutoff="09:00:00"):
    year, month = data["year"], data["month"]
    n = calendar.monthrange(year, month)[1]
    cut = hms_to_sec(cutoff) if cutoff.count(":") == 2 else hms_to_sec(cutoff + ":00")
    sundays, holidays = set(sundays), set(holidays)
    out = []
    for s in data["staff"]:
        R = s["rows"]
        get = lambda k, d: (R.get(k, {}).get(d, "") or "")
        days, present = {}, 0
        late_days = leave_days = 0
        late_total = 0
        for d in range(1, n + 1):
            tin, tout = hms_to_sec(get("in", d)), hms_to_sec(get("out", d))
            shift = parse_shift(get("shift", d))
            if d in holidays:
                status = HOL
            elif d in sundays:
                status = SUN
            elif tin is not None or tout is not None:
                status = PRESENT
            else:
                status = LEAVE
            late = early = 0
            if status == PRESENT:
                present += 1
                if tin is not None and tin > cut:
                    late = tin - cut
                    late_days += 1
                    late_total += late
                if tout is not None and shift["end"] and shift["code"] != "WO" and tout < shift["end"]:
                    early = shift["end"] - tout
            elif status == LEAVE:
                leave_days += 1
            tot = hms_to_sec(get("total", d)) or 0
            days[d] = {
                "status": status,
                "in": get("in", d) if tin is not None else "-",
                "out": get("out", d) if tout is not None else "-",
                "total": sec_to_hms(tot),
                "shift": shift["label"] if shift["label"] and set(shift["label"]) != {"-"} else "--",
                "late": sec_to_hms(late), "early": sec_to_hms(early),
                "perm": get("perm", d) or "-", "half": get("half", d) or "-",
                "is_late": late > 0,
            }
        working = n - len(sundays | holidays)
        out.append({**{k: s[k] for k in ("slno", "emp_id", "name", "role", "dept", "designation", "doj")},
                    "days": days, "working": working, "late": late_days,
                    "leave": leave_days, "present": present,
                    "late_total": sec_to_hms(late_total)})
    return out
