import calendar
import io
import re
import uuid
import zipfile
from flask import Flask, jsonify, render_template, request, send_file

from csv_parser import parse_csv
from calc import calculate
from report import build_pdf
from nlp_utils import parse_days_text

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
STORE = {}  # token -> parsed CSV (in memory)


def _sundays(year, month):
    return [d for d in range(1, calendar.monthrange(year, month)[1] + 1)
            if calendar.weekday(year, month, d) == 6]
def _results(payload):
    data = STORE.get(payload.get("token"))
    if not data:
        raise ValueError("Session expired - please upload the CSV again.")
    res = calculate(data, payload.get("sundays", []), payload.get("holidays", []),
                    payload.get("cutoff") or "09:00:00")
    return data, res
@app.route("/")
def index():
    return render_template("index.html")
@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="No file received."), 400
    try:
        data = parse_csv(f.read())
    except Exception as e:
        return jsonify(error=str(e)), 400
    token = uuid.uuid4().hex
    STORE[token] = data
    while len(STORE) > 20:
        STORE.pop(next(iter(STORE)))
    y, m = data["year"], data["month"]
    return jsonify(token=token, year=y, month=m, month_name=calendar.month_name[m],
                   first_weekday=(calendar.weekday(y, m, 1) + 1) % 7,  # Sunday-first grid
                   days=calendar.monthrange(y, m)[1], sundays=_sundays(y, m),
                   title=data["title"],
                   staff=[{"emp_id": s["emp_id"], "name": s["name"]} for s in data["staff"]])
@app.post("/api/nlp")
def nlp():
    p = request.get_json()
    return jsonify(days=parse_days_text(p.get("text", ""), int(p["year"]), int(p["month"])))
@app.post("/api/summary")
def summary():
    try:
        _, res = _results(request.get_json())
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(rows=[{k: r[k] for k in ("slno", "emp_id", "name", "designation", "working",
                                           "present", "late", "leave", "late_total")} for r in res])
@app.post("/api/pdf")
def pdf():
    p = request.get_json()
    try:
        data, res = _results(p)
    except Exception as e:
        return jsonify(error=str(e)), 400
    only = {p["emp_id"]} if p.get("emp_id") else None
    name = f"{calendar.month_abbr[data['month']].upper()}_{data['year']}_attendance_report"
    if p.get("emp_id"):
        name += "_" + re.sub(r"\W+", "_", p["emp_id"])
    return send_file(io.BytesIO(build_pdf(res, data, only)), mimetype="application/pdf",
                     as_attachment=True, download_name=name + ".pdf")
@app.post("/api/zip")
def zip_all():
    p = request.get_json()
    try:
        data, res = _results(p)
    except Exception as e:
        return jsonify(error=str(e)), 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in res:
            fn = re.sub(r"[^\w\-]+", "_", f"{r['slno']}_{r['emp_id']}_{r['name']}") + ".pdf"
            z.writestr(fn, build_pdf(res, data, {r["emp_id"]}))
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"{calendar.month_abbr[data['month']].upper()}_{data['year']}_staff_reports.zip")


if __name__ == "__main__":
    app.run(debug=True)
