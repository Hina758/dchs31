# app.py
import sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, jsonify, send_file, abort
from io import StringIO, BytesIO
import csv
import os
from datetime import datetime

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
      CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        studentNo TEXT NOT NULL,
        name TEXT NOT NULL,
        crush TEXT NOT NULL,
        createdAt TEXT NOT NULL,
        UNIQUE(studentNo, name)
      )
    ''')
    db.execute('''
      CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
      )
    ''')
    cur = db.execute("SELECT value FROM meta WHERE key='public'")
    if cur.fetchone() is None:
        db.execute("INSERT INTO meta (key, value) VALUES ('public','false')")
    db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_public_flag():
    db = get_db()
    r = db.execute("SELECT value FROM meta WHERE key='public'").fetchone()
    return (r and r['value'] == 'true')

def set_public_flag(flag: bool):
    db = get_db()
    db.execute("REPLACE INTO meta (key, value) VALUES ('public', ?)", ('true' if flag else 'false',))
    db.commit()

with app.app_context():
    init_db()

# --- constants for admin codes ---
ADMIN1_CODE = '01911'
ADMIN1_NAMES = ['이재율', '박준혁']
ADMIN2_CODE = '77777'
ADMIN2_NAME = '허찬영'
ADMIN2_CRUSH = '한승원'

# --- routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json or request.form
    studentNo = (data.get('studentNo') or data.get('studentId') or '').strip()
    name = (data.get('name') or '').strip()
    crush = (data.get('crush') or '').strip()
    if not (studentNo and name and crush):
        return jsonify({'ok': False, 'error': 'missing'}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO submissions (studentNo,name,crush,createdAt) VALUES (?,?,?,?)",
            (studentNo, name, crush, datetime.utcnow().isoformat())
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'ok': False, 'error': 'duplicate'}), 409
    return jsonify({'ok': True})

@app.route('/result-wait')
def result_wait():
    return render_template('result_wait.html')

@app.route('/check', methods=['GET', 'POST'])
def check():
    if request.method == 'GET':
        return render_template('check.html')
    studentNo = (request.form.get('studentNo') or '').strip()
    if not studentNo:
        return render_template('check.html', error='학번을 입력하세요.')
    db = get_db()
    row = db.execute("SELECT * FROM submissions WHERE studentNo = ?", (studentNo,)).fetchone()
    public = get_public_flag()
    if not row:
        return render_template('check.html', error='해당 학번의 제출 기록을 찾을 수 없습니다.')
    if not public:
        return render_template('check.html', error='관리자가 결과를 공개하지 않았습니다. 공개될 때까지 기다려주세요.')
    my = row
    reciprocal = db.execute(
        "SELECT * FROM submissions WHERE name=? AND crush=?",
        (my['crush'], my['name'])
    ).fetchone()
    matched = True if reciprocal else False
    return render_template('result.html', matched=matched, myname=my['name'], crush=my['crush'])

@app.route('/api/public')
def api_public():
    return jsonify({'public': bool(get_public_flag())})

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    participant_count = get_db().execute("SELECT COUNT(*) AS cnt FROM submissions").fetchone()['cnt']
    public_flag = get_public_flag()

    if request.method == 'GET':
        return render_template('admin.html', participantCount=participant_count, public=public_flag)

    # POST Logic
    code = (request.form.get('code') or '').strip()
    name = (request.form.get('name') or '').strip()

    if not (code == ADMIN1_CODE and name in ADMIN1_NAMES):
        return render_template('admin.html', error='권한 없음', participantCount=participant_count, public=public_flag)

    action = request.form.get('action')
    if action == 'toggle':
        new_flag = not public_flag
        set_public_flag(new_flag)
        status_text = "공개" if new_flag else "비공개"
        success_msg = f'공개 상태를 \'{status_text}\'(으)로 변경했습니다.'
        return render_template('admin.html', success=success_msg, participantCount=participant_count, public=new_flag)

    return render_template('admin.html', participantCount=participant_count, public=public_flag)

@app.route('/admin2', methods=['GET', 'POST'])
def admin2():
    def get_all_data():
        rows = get_db().execute("SELECT * FROM submissions ORDER BY createdAt DESC").fetchall()
        rows = [dict(r) for r in rows]
        pairs = set()
        for r in rows:
            rec = [x for x in rows if x['name'] == r['crush'] and x['crush'] == r['name']]
            if rec:
                key = tuple(sorted([r['name'], rec[0]['name']]))
                pairs.add(key)
        stats = {'participantCount': len(rows), 'matchCount': len(pairs)}
        return rows, stats

    entries, stats = get_all_data()

    if request.method == 'GET':
        return render_template('admin2.html', entries=entries, stats=stats)

    # POST Logic for auth check (mostly for CSV export)
    code = (request.form.get('code') or '').strip()
    name = (request.form.get('name') or '').strip()
    crush = (request.form.get('crush') or '').strip()

    if not (code == ADMIN2_CODE and name == ADMIN2_NAME and crush == ADMIN2_CRUSH):
        return render_template('admin2.html', error='권한 없음', entries=entries, stats=stats)

    return render_template('admin2.html', entries=entries, stats=stats)

@app.route('/admin2/export', methods=['POST'])
def admin2_export():
    code = (request.form.get('code') or '').strip()
    name = (request.form.get('name') or '').strip()
    crush = (request.form.get('crush') or '').strip()

    if not (code == ADMIN2_CODE and name == ADMIN2_NAME and crush == ADMIN2_CRUSH):
        abort(403)

    rows = get_db().execute("SELECT * FROM submissions ORDER BY createdAt DESC").fetchall()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id', 'studentNo', 'name', 'crush', 'createdAt'])
    for r in rows:
        cw.writerow([r['id'], r['studentNo'], r['name'], r['crush'], r['createdAt']])
    output = si.getvalue()
    return send_file(
        BytesIO(output.encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='entries.csv'
    )

@app.route('/ping')
def ping():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)