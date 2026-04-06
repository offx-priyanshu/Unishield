"""
SNOX Security System - Complete Backend
Flask + SQLite
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3, hashlib, datetime, os, requests, threading, time, json

app = Flask(__name__)
CORS(app)
DB_PATH = "snox.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS outpasses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sid TEXT NOT NULL,
        student_name TEXT,
        destination TEXT NOT NULL,
        purpose TEXT,
        duration_hours INTEGER DEFAULT 2,
        status TEXT DEFAULT 'PENDING',
        qr_token TEXT UNIQUE,
        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at DATETIME,
        approved_by TEXT,
        exit_time DATETIME,
        return_time DATETIME,
        expected_return DATETIME,
        rejection_reason TEXT
    );
    CREATE TABLE IF NOT EXISTS violations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sid TEXT NOT NULL,
        reason TEXT NOT NULL,
        severity TEXT DEFAULT 'LOW',
        added_by TEXT,
        notes TEXT,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        title TEXT,
        message TEXT,
        sid TEXT,
        outpass_id INTEGER,
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_phone TEXT,
        message TEXT,
        template_type TEXT,
        provider TEXT,
        status TEXT DEFAULT 'PENDING',
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        response TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    INSERT OR IGNORE INTO settings VALUES ('violation_limit','3');
    INSERT OR IGNORE INTO settings VALUES ('sms_auto_exit','1');
    INSERT OR IGNORE INTO settings VALUES ('sms_auto_return','1');
    INSERT OR IGNORE INTO settings VALUES ('sms_auto_overdue','1');
    INSERT OR IGNORE INTO settings VALUES ('fast2sms_key','');
    INSERT OR IGNORE INTO settings VALUES ('twilio_sid','');
    INSERT OR IGNORE INTO settings VALUES ('twilio_token','');
    INSERT OR IGNORE INTO settings VALUES ('twilio_from','');
    """)
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", [key]).fetchone()
    conn.close()
    return row["value"] if row else default

def generate_qr_token(outpass_id, sid):
    raw = f"SNOX-{outpass_id}-{sid}-{datetime.datetime.now().timestamp()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16].upper()

def create_notification(ntype, sid, title, message, outpass_id=None):
    conn = get_db()
    conn.execute("INSERT INTO notifications (type,sid,title,message,outpass_id) VALUES (?,?,?,?,?)",
                 [ntype, sid, title, message, outpass_id])
    conn.commit()
    conn.close()

SMS_TEMPLATES = {
    "EXIT_ALERT":        "SNOX ALERT: {name} (SID:{sid}) left campus at {time}. Dest: {dest}. Return by: {return_time}.",
    "RETURN_CONFIRM":    "SNOX: {name} safely returned at {time}. -Campus Security",
    "OVERDUE_ALERT":     "URGENT SNOX: {name} ({sid}) OVERDUE since {time}. Contact security.",
    "OUTPASS_APPROVED":  "SNOX: Outpass APPROVED for {dest}. Show QR at gate. Valid till {time}.",
    "OUTPASS_REJECTED":  "SNOX: Outpass rejected. Reason: {reason}.",
    "VIOLATION_WARNING": "SNOX WARNING: {name} has {count} violations. Account may be suspended.",
    "BLACKLIST_ALERT":   "SNOX: Your access is SUSPENDED after {count} violations. Contact admin."
}

def send_sms(phone, template_type, variables):
    if not phone or len(phone) < 10:
        return {"success": False}
    message = SMS_TEMPLATES.get(template_type, "SNOX Alert").format(**variables)
    f2s_key = get_setting("fast2sms_key")
    status = "FAILED"
    provider = "none"
    response_text = ""
    if f2s_key:
        try:
            r = requests.post("https://www.fast2sms.com/dev/bulkV2",
                headers={"Authorization": f2s_key},
                json={"route":"q","numbers":phone,"message":message,"flash":0}, timeout=8)
            if r.json().get("return"):
                status = "SENT"; provider = "fast2sms"
        except Exception as e:
            response_text = str(e)
    if status != "SENT":
        sid2 = get_setting("twilio_sid"); token = get_setting("twilio_token"); frm = get_setting("twilio_from")
        if sid2 and token:
            try:
                r = requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid2}/Messages.json",
                    auth=(sid2,token), data={"From":frm,"To":f"+91{phone}","Body":message}, timeout=8)
                if r.status_code == 201:
                    status = "SENT"; provider = "twilio"
            except Exception as e:
                response_text = str(e)
    conn = get_db()
    conn.execute("INSERT INTO sms_logs(recipient_phone,message,template_type,provider,status,response) VALUES(?,?,?,?,?,?)",
                 [phone,message,template_type,provider,status,response_text])
    conn.commit(); conn.close()
    return {"success": status=="SENT", "provider": provider}

# ── OUTPASS ROUTES ──
@app.route("/api/outpass/submit", methods=["POST"])
def submit_outpass():
    data = request.json
    sid = data.get("sid")
    hours = int(data.get("duration_hours", 2))
    expected = (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO outpasses(sid,student_name,destination,purpose,duration_hours,expected_return) VALUES(?,?,?,?,?,?)",
        [sid, data.get("student_name"), data.get("destination"), data.get("purpose"), hours, expected])
    oid = cursor.lastrowid
    conn.commit(); conn.close()
    create_notification("NEW_OUTPASS", sid, "New Outpass Request",
        f"{data.get('student_name')} wants to go to {data.get('destination')}", oid)
    return jsonify({"success": True, "outpass_id": oid, "expected_return": expected})

@app.route("/api/outpass/all", methods=["GET"])
def get_all_outpasses():
    status = request.args.get("status","ALL")
    conn = get_db()
    rows = conn.execute("SELECT * FROM outpasses" + ("" if status=="ALL" else " WHERE status=?") + " ORDER BY requested_at DESC LIMIT 100",
                        [] if status=="ALL" else [status]).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/outpass/approve/<int:oid>", methods=["POST"])
def approve_outpass(oid):
    data = request.json
    token = generate_qr_token(oid, "")
    conn = get_db()
    outpass = conn.execute("SELECT * FROM outpasses WHERE id=?", [oid]).fetchone()
    conn.execute("UPDATE outpasses SET status='APPROVED',approved_at=datetime('now'),approved_by=?,qr_token=? WHERE id=?",
                 [data.get("approved_by","admin"), token, oid])
    conn.commit(); conn.close()
    return jsonify({"success": True, "qr_token": token})

@app.route("/api/outpass/reject/<int:oid>", methods=["POST"])
def reject_outpass(oid):
    data = request.json
    conn = get_db()
    conn.execute("UPDATE outpasses SET status='REJECTED',rejection_reason=? WHERE id=?",
                 [data.get("reason","Not specified"), oid])
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/outpass/verify-qr", methods=["POST"])
def verify_qr():
    token = request.json.get("token","").strip()
    conn = get_db()
    row = conn.execute("SELECT * FROM outpasses WHERE qr_token=?", [token]).fetchone()
    conn.close()
    if not row: return jsonify({"valid":False,"reason":"QR not found"})
    if row["status"] not in ("APPROVED","ACTIVE"): return jsonify({"valid":False,"reason":f"Status is {row['status']}"})
    if row["expected_return"]:
        exp = datetime.datetime.strptime(row["expected_return"],"%Y-%m-%d %H:%M:%S")
        if datetime.datetime.now() > exp: return jsonify({"valid":False,"reason":"Outpass EXPIRED"})
    return jsonify({"valid":True,"sid":row["sid"],"student_name":row["student_name"],
                    "destination":row["destination"],"expected_return":row["expected_return"],
                    "status":row["status"],"outpass_id":row["id"]})

@app.route("/api/outpass/exit/<int:oid>", methods=["POST"])
def mark_exit(oid):
    conn = get_db()
    conn.execute("UPDATE outpasses SET status='ACTIVE',exit_time=datetime('now') WHERE id=?", [oid])
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/outpass/return/<int:oid>", methods=["POST"])
def mark_return(oid):
    conn = get_db()
    conn.execute("UPDATE outpasses SET status='COMPLETED',return_time=datetime('now') WHERE id=?", [oid])
    conn.commit(); conn.close()
    return jsonify({"success": True})

@app.route("/api/outpass/status/<int:oid>", methods=["GET"])
def outpass_status(oid):
    conn = get_db()
    row = conn.execute("SELECT * FROM outpasses WHERE id=?", [oid]).fetchone()
    conn.close()
    return jsonify(dict(row)) if row else (jsonify({"error":"Not found"}),404)

@app.route("/api/outpass/student/<sid>", methods=["GET"])
def student_outpasses(sid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM outpasses WHERE sid=? ORDER BY requested_at DESC", [sid]).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ── NOTIFICATION ROUTES ──
@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    conn = get_db()
    rows = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50").fetchall()
    unread = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE is_read=0").fetchone()["c"]
    conn.close()
    return jsonify({"notifications":[dict(r) for r in rows],"unread_count":unread})

@app.route("/api/notifications/mark-read", methods=["POST"])
def mark_read():
    nid = request.json.get("id")
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read=1" + (" WHERE id=?" if nid else ""), [nid] if nid else [])
    conn.commit(); conn.close()
    return jsonify({"success": True})

# ── VIOLATION ROUTES ──
@app.route("/api/violations/add", methods=["POST"])
def add_violation():
    data = request.json
    sid = data.get("sid")
    conn = get_db()
    conn.execute("INSERT INTO violations(sid,reason,severity,added_by,notes) VALUES(?,?,?,?,?)",
                 [sid,data.get("reason"),data.get("severity","LOW"),data.get("added_by","admin"),data.get("notes","")])
    conn.execute("UPDATE students SET violation_count=violation_count+1 WHERE sid=?", [sid])
    count_row = conn.execute("SELECT violation_count FROM students WHERE sid=?", [sid]).fetchone()
    count = count_row["violation_count"] if count_row else 1
    limit = int(get_setting("violation_limit","3"))
    conn.commit()
    blacklisted = False
    if count >= limit:
        conn.execute("UPDATE students SET security_access='BLACKLISTED' WHERE sid=?", [sid])
        conn.commit()
        blacklisted = True
        create_notification("BLACKLIST", sid, "Student Auto-Blacklisted",
            f"Student {sid} blacklisted after {count} violations")
    conn.close()
    return jsonify({"success":True,"violation_count":count,"blacklisted":blacklisted})

@app.route("/api/violations/<sid>", methods=["GET"])
def get_violations(sid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM violations WHERE sid=? ORDER BY added_at DESC", [sid]).fetchall()
    student = conn.execute("SELECT violation_count,violation_limit FROM students WHERE sid=?", [sid]).fetchone()
    conn.close()
    return jsonify({"violations":[dict(r) for r in rows],
                    "count":student["violation_count"] if student else 0,
                    "limit":student["violation_limit"] if student else 3})

@app.route("/api/violations/reset/<sid>", methods=["POST"])
def reset_violations(sid):
    conn = get_db()
    conn.execute("UPDATE students SET violation_count=0,security_access='APPROVED' WHERE sid=?", [sid])
    conn.execute("DELETE FROM violations WHERE sid=?", [sid])
    conn.commit(); conn.close()
    return jsonify({"success": True})

# ── SMS ROUTES ──
@app.route("/api/sms/send", methods=["POST"])
def manual_sms():
    data = request.json
    result = send_sms(data.get("phone"), data.get("template","EXIT_ALERT"), data.get("variables",{}))
    return jsonify(result)

@app.route("/api/sms/logs", methods=["GET"])
def sms_logs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sms_logs ORDER BY sent_at DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/sms/templates", methods=["GET"])
def sms_templates():
    return jsonify(SMS_TEMPLATES)

@app.route("/api/settings/update", methods=["POST"])
def update_settings():
    conn = get_db()
    for k,v in request.json.items():
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", [k,v])
    conn.commit(); conn.close()
    return jsonify({"success": True})

# ── DASHBOARD ──
@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    conn = get_db()
    def cnt(q, p=[]): return conn.execute(q,p).fetchone()[0]
    stats = {
        "total_students": cnt("SELECT COUNT(*) FROM students"),
        "currently_out":  cnt("SELECT COUNT(*) FROM outpasses WHERE status='ACTIVE'"),
        "pending_requests": cnt("SELECT COUNT(*) FROM outpasses WHERE status='PENDING'"),
        "blacklisted":    cnt("SELECT COUNT(*) FROM students WHERE security_access='BLACKLISTED'"),
        "unread_notifications": cnt("SELECT COUNT(*) FROM notifications WHERE is_read=0"),
        "recent_activity": [dict(r) for r in conn.execute(
            "SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10").fetchall()]
    }
    conn.close()
    return jsonify(stats)

def check_overdue():
    while True:
        time.sleep(300)
        try:
            conn = get_db()
            rows = conn.execute("""SELECT o.*,s.phone,s.full_name FROM outpasses o
                LEFT JOIN students s ON o.sid=s.sid
                WHERE o.status='ACTIVE' AND o.expected_return < datetime('now')
                AND o.expected_return > datetime('now','-1 hour')""").fetchall()
            conn.close()
            for r in rows:
                create_notification("OVERDUE",r["sid"],"Student Overdue",
                    f"{r['full_name']} overdue since {r['expected_return']}")
                if r["phone"]:
                    send_sms(r["phone"],"OVERDUE_ALERT",{"name":r["full_name"],"sid":r["sid"],"time":r["expected_return"]})
        except: pass

if __name__ == "__main__":
    init_db()
    threading.Thread(target=check_overdue, daemon=True).start()
    app.run(debug=True, port=5000)
