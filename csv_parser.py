import csv
import io
import re
from nlp_utils import match_label

DATE_RE = re.compile(r"^\s*(\d{1,2})-(\d{1,2})-(\d{2,4})\s*$")


def _decode(raw):
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


def parse_csv(raw):
    rows = list(csv.reader(io.StringIO(_decode(raw))))
    best, hdr_idx = 0, None
    for i, r in enumerate(rows):
        c = sum(1 for x in r if DATE_RE.match(x))
        if c > best:
            best, hdr_idx = c, i
    if hdr_idx is None or best < 20:
        raise ValueError("Could not find the date header row (dd-mm-yyyy columns) in this CSV.")
    hdr = rows[hdr_idx]
    date_cols = {}
    for ci, x in enumerate(hdr):
        m = DATE_RE.match(x)
        if m:
            d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = y + 2000 if y < 100 else y
            date_cols[ci] = (y, mo, d)
    first_date_col = min(date_cols)
    label_col = first_date_col - 1
    year, month = next(iter(date_cols.values()))[:2]
    title = [" ".join(x.strip() for x in r if x.strip()).strip(" ,")
             for r in rows[:hdr_idx]]
    title = [t for t in title if t][:3]

    staff, cur = [], None
    for r in rows[hdr_idx + 1:]:
        if len(r) <= label_col:
            continue
        lab = match_label(r[label_col])
        if lab == "in" and (r[0].strip() or r[1].strip()):
            cur = {
                "slno": r[0].strip(), "emp_id": r[1].strip(), "name": r[2].strip(),
                "role": r[3].strip(), "dept": r[4].strip(),
                "designation": r[5].strip(), "doj": r[6].strip(), "rows": {},
            }
            staff.append(cur)
        if cur is None or lab is None:
            continue
        cur["rows"][lab] = {d[2]: (r[ci].strip() if ci < len(r) else "")
                            for ci, d in date_cols.items()}
    if not staff:
        raise ValueError("No employee blocks found in this CSV.")
    return {"title": title, "year": year, "month": month, "staff": staff}
