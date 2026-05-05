import base64
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

import qrcode
from flask import Blueprint, make_response, render_template_string, request

attendance_bp = Blueprint("attendance", __name__)

DATABASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "attendance.db")
QR_EXPIRY_SECONDS = 5
ACTIVE_TOKENS = {}


QR_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>QR Attendance</title>
    <meta http-equiv="refresh" content="{{ expiry }}">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
        #countdown { font-size: 20px; font-weight: bold; color: #dc3545; margin-top: 20px; }
        #nextqr { font-size: 16px; color: #888; margin-top: 10px; }
    </style>
</head>
<body>
    <h2>Scan this QR code. Valid for <span id="seconds">{{ expiry }}</span> seconds.</h2>
    <img id="qr-img" src="data:image/png;base64,{{ qr }}">
    <div id="countdown">QR expires in: {{ expiry }} seconds</div>
    <div id="nextqr"></div>
    <script>
        let timer = {{ expiry }};
        const countdown = document.getElementById('countdown');
        const nextQR = document.getElementById('nextqr');
        const qrImg = document.getElementById('qr-img');
        const secondsSpan = document.getElementById('seconds');
        const interval = setInterval(() => {
            timer--;
            secondsSpan.textContent = timer;
            if (timer > 0) {
                countdown.textContent = `QR expires in: ${timer} second${timer !== 1 ? 's' : ''}`;
            } else {
                countdown.textContent = "QR Code Expired";
                qrImg.style.display = "none";
                clearInterval(interval);
                let regen = 5;
                nextQR.textContent = `Next QR in ${regen} seconds...`;
                const regenInterval = setInterval(() => {
                    regen--;
                    nextQR.textContent = `Next QR in ${regen} second${regen !== 1 ? 's' : ''}...`;
                    if (regen === 0) {
                        clearInterval(regenInterval);
                        location.reload();
                    }
                }, 1000);
            }
        }, 1000);
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!doctype html>
<title>Login</title>
<h2>Login to mark attendance</h2>
<form method="post">
  <label>1AM24EC</label><input type="text" name="usn" placeholder="e.g., 143" required><br>
  <label>Password</label><input type="password" name="password" required><br>
  <input type="submit" value="Login">
</form>
<p>{{ msg }}</p>
<p>No account? <a href="{{ register_url }}">Register here</a></p>
"""

REGISTER_TEMPLATE = """
<!doctype html>
<title>Register</title>
<h2>Create your account</h2>
<form method="post">
  <label>1AM24EC</label><input type="text" name="usn" placeholder="e.g., 143" required><br>
  <label>Password</label><input type="password" name="password" required><br>
  <input type="submit" value="Register">
</form>
<p>{{ msg }}</p>
<p>Already registered? <a href="{{ home_url }}">Login</a></p>
"""

SUCCESS_TEMPLATE = """
<!doctype html>
<title>Success</title>
<h2>{{ message }}</h2>
"""


def get_conn():
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usn TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                usn TEXT NOT NULL,
                FOREIGN KEY (usn) REFERENCES Users(usn)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS Attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usn TEXT NOT NULL,
                session TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'P',
                marked_at TEXT NOT NULL,
                UNIQUE(usn, session),
                FOREIGN KEY (usn) REFERENCES Users(usn)
            )
            """
        )


@attendance_bp.record_once
def on_load(_):
    init_db()


def generate_qr_token():
    token = str(uuid.uuid4())
    ACTIVE_TOKENS[token] = datetime.utcnow()
    return token


def cleanup_tokens():
    now = datetime.utcnow()
    for token in list(ACTIVE_TOKENS.keys()):
        if now - ACTIVE_TOKENS[token] > timedelta(seconds=QR_EXPIRY_SECONDS):
            del ACTIVE_TOKENS[token]


def get_device_id(req):
    return req.cookies.get("device_id") or str(uuid.uuid4())


def get_current_session():
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now_ist.time()
    schedule = [
        ("09:15", "10:10", "1st Hour"),
        ("10:10", "11:05", "2nd Hour"),
        ("11:05", "11:20", "Short Break"),
        ("11:20", "12:15", "3rd Hour"),
        ("12:15", "13:10", "4th Hour"),
        ("13:10", "14:00", "Lunch Break"),
        ("14:00", "14:55", "5th Hour"),
        ("14:55", "15:50", "6th Hour"),
        ("15:50", "16:45", "7th Hour"),
    ]
    for start, end, label in schedule:
        if datetime.strptime(start, "%H:%M").time() <= current_time < datetime.strptime(end, "%H:%M").time():
            return label
    return "Not within any class hour."


@attendance_bp.route("/")
def qr_page():
    cleanup_tokens()
    token = generate_qr_token()
    url = request.url_root.rstrip("/") + request.script_root + f"/attendance/submit/{token}"
    qr_img = qrcode.make(url)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return render_template_string(QR_TEMPLATE, qr=qr_str, expiry=QR_EXPIRY_SECONDS)


@attendance_bp.route("/submit/<token>", methods=["GET", "POST"])
def submit(token):
    cleanup_tokens()
    if token not in ACTIVE_TOKENS:
        return render_template_string(SUCCESS_TEMPLATE, message="QR code expired or invalid.")

    device_id = get_device_id(request)

    with get_conn() as conn:
        existing_device = conn.execute(
            "SELECT usn FROM Devices WHERE device_id = ?",
            (device_id,),
        ).fetchone()

        if existing_device:
            usn = existing_device["usn"]
            session = datetime.now().strftime("%d-%m") + " (" + get_current_session() + ")"
            return mark_attendance(usn, session, device_id, token)

        if request.method == "POST":
            suffix = request.form.get("usn", "").strip().upper()
            password = request.form.get("password", "").strip()
            usn = f"1AM24EC{suffix}"

            user = conn.execute(
                "SELECT 1 FROM Users WHERE usn = ? AND password = ?",
                (usn, password),
            ).fetchone()
            if not user:
                return render_template_string(
                    LOGIN_TEMPLATE,
                    msg="Invalid USN or password",
                    register_url=request.script_root + "/attendance/register",
                )

            conn.execute(
                "INSERT OR IGNORE INTO Devices(device_id, usn) VALUES (?, ?)",
                (device_id, usn),
            )
            conn.commit()
            session = datetime.now().strftime("%d-%m") + " (" + get_current_session() + ")"
            return mark_attendance(usn, session, device_id, token)

    resp = make_response(
        render_template_string(
            LOGIN_TEMPLATE,
            msg="",
            register_url=request.script_root + "/attendance/register",
        )
    )
    resp.set_cookie("device_id", device_id, max_age=31536000)
    return resp


@attendance_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        suffix = request.form.get("usn", "").strip().upper()
        password = request.form.get("password", "").strip()
        usn = f"1AM24EC{suffix}"
        with get_conn() as conn:
            exists = conn.execute("SELECT 1 FROM Users WHERE usn = ?", (usn,)).fetchone()
            if exists:
                return render_template_string(
                    REGISTER_TEMPLATE,
                    msg="USN already registered.",
                    home_url=request.script_root + "/attendance/",
                )
            conn.execute("INSERT INTO Users(usn, password) VALUES (?, ?)", (usn, password))
            conn.commit()
        return render_template_string(SUCCESS_TEMPLATE, message="Registration successful.")

    return render_template_string(
        REGISTER_TEMPLATE,
        msg="",
        home_url=request.script_root + "/attendance/",
    )


def mark_attendance(usn, session, device_id, token):
    if "Not within any class hour." in session:
        del ACTIVE_TOKENS[token]
        return make_response(
            render_template_string(
                SUCCESS_TEMPLATE,
                message="Not in class hours. Attendance blocked.",
            )
        )

    with get_conn() as conn:
        exists = conn.execute(
            "SELECT status FROM Attendance WHERE usn = ? AND session = ?",
            (usn, session),
        ).fetchone()
        if exists and exists["status"] == "P":
            msg = f"{usn} already marked Present for {session}"
        else:
            conn.execute(
                """
                INSERT INTO Attendance(usn, session, status, marked_at)
                VALUES (?, ?, 'P', ?)
                ON CONFLICT(usn, session)
                DO UPDATE SET status='P', marked_at=excluded.marked_at
                """,
                (usn, session, datetime.utcnow().isoformat()),
            )
            conn.commit()
            msg = f"{usn} marked Present for {session}"

    del ACTIVE_TOKENS[token]
    resp = make_response(render_template_string(SUCCESS_TEMPLATE, message=msg))
    resp.set_cookie("device_id", device_id, max_age=31536000)
    resp.set_cookie("user_usn", usn, max_age=31536000)
    return resp


@attendance_bp.route("/admin")
def admin():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT usn, session, status, marked_at FROM Attendance ORDER BY usn, session"
        ).fetchall()
    if not rows:
        return "No attendance data yet."

    headers = ["USN", "Session", "Status", "Marked At"]
    table = "<table border='1' cellpadding='5'><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    for row in rows:
        table += (
            "<tr>"
            f"<td>{row['usn']}</td>"
            f"<td>{row['session']}</td>"
            f"<td>{row['status']}</td>"
            f"<td>{row['marked_at']}</td>"
            "</tr>"
        )
    table += "</table>"
    return table
