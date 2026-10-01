# Staff Attendance Report Generator (Flask + Python NLP helpers)

## Run
    pip install -r requirements.txt
    python app.py
    open http://127.0.0.1:5000

## Use
1. Upload the HR biometric CSV (month is detected automatically).
2. In the calendar pick **Sunday** (yellow) or **Holiday** (sky blue) and click dates
   (Sundays are pre-filled). Or type e.g. `4th, 12 to 14 and 24 Sep` and click *Apply as holidays*.
3. Click **Calculate**, then download one PDF (one page per staff) or a ZIP of separate PDFs.

## Rules
- Late  = in-time later than 09:00:00 on a working day (violet)
- Leave = working day with no punch (light orange)
- Sunday = yellow, college holiday = sky blue (not counted as working/late/leave)
- Working days = days in month - Sundays - holidays

## Files
app.py (web server) | csv_parser.py (reads HR CSV) | calc.py (late/leave logic)
report.py (PDF pages) | nlp_utils.py (fuzzy labels, shift-text and holiday-sentence parsing)
