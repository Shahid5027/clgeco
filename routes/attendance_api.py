import sqlite3
import qrcode
from flask import Blueprint, render_template_string, request, make_response, current_app, session, redirect, url_for, flash
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import base64
from io import BytesIO
import uuid
import os

attendance_bp = Blueprint('attendance', __name__)

qr_expiry_seconds = 5
active_tokens = {}

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'attendance.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            usn TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Devices (
            device_id TEXT PRIMARY KEY,
            usn TEXT NOT NULL,
            FOREIGN KEY (usn) REFERENCES Users (usn)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usn TEXT NOT NULL,
            session TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usn) REFERENCES Users (usn)
        )
    ''')
    conn.commit()
    conn.close()

# HTML Templates
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
    <div id="countdown">⏳ QR expires in: {{ expiry }} seconds</div>
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
                countdown.textContent = `⏳ QR expires in: ${timer} second${timer !== 1 ? 's' : ''}`;
            } else {
                countdown.textContent = "❌ QR Code Expired!";
                qrImg.style.display = "none";
                clearInterval(interval);

                let regen = 5;
                nextQR.textContent = `🔄 Next QR in ${regen} seconds...`;

                const regenInterval = setInterval(() => {
                    regen--;
                    nextQR.textContent = `🔄 Next QR in ${regen} second${regen !== 1 ? 's' : ''}...`;
                    if (regen === 0) {
                        clearInterval(regenInterval);
                        location.reload(); // Auto-refresh the page to load new QR
                    }
                }, 1000);
            }
        }, 1000);
    </script>
    <footer style="margin-top: 40px; font-size: 14px; color: #666;">
        <hr style="width: 60%; border: 0.5px solid #ccc;">
        <div style="margin-top: 10px;">
            Developed by <strong>Team RAGE</strong> | Department of ECE | AMC Engineering College
        </div>
    </footer>

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
<p>No account? <a href="/attendance/register">Register here</a></p>
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
<p>Already registered? <a href="/attendance/">Login</a></p>
"""

SUCCESS_TEMPLATE = """
<!doctype html>
<title>Success</title>
<h2>{{ message }}</h2>
"""

# Utility Functions
def generate_qr_token():
    token = str(uuid.uuid4())
    active_tokens[token] = datetime.utcnow()
    return token

def cleanup_tokens():
    now = datetime.utcnow()
    for token in list(active_tokens.keys()):
        if now - active_tokens[token] > timedelta(seconds=qr_expiry_seconds):
            del active_tokens[token]

def get_device_id(req):
    device_id = req.cookies.get("device_id")
    if not device_id:
        device_id = str(uuid.uuid4())
    return device_id

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
        ("15:50", "16:45", "7th Hour")
    ]

    for start, end, label in schedule:
        if datetime.strptime(start, "%H:%M").time() <= current_time < datetime.strptime(end, "%H:%M").time():
            return label

    return "⚠️ Not within any class hour."

# Flask Routes
@attendance_bp.route("/")
def qr_page():
    if session.get('role') not in ['faculty', 'admin']:
        flash("Unauthorized access. Only faculty can generate attendance QRs.")
        return redirect(url_for('index'))
        
    init_db()  # Ensure database is initialized before any access
    cleanup_tokens()
    token = generate_qr_token()
    url = f"https://{request.host}/attendance/submit/{token}"  # Note the blueprint prefix
    qr_img = qrcode.make(url)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return render_template_string(QR_TEMPLATE, qr=qr_str, expiry=qr_expiry_seconds)

@attendance_bp.route("/submit/<token>", methods=["GET", "POST"])
def submit(token):
    init_db()
    cleanup_tokens()
    if token not in active_tokens:
        return render_template_string(SUCCESS_TEMPLATE, message="❌ QR Code expired or invalid.")

    device_id = get_device_id(request)
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT usn FROM Devices WHERE device_id = ?', (device_id,))
    existing_device = c.fetchone()
    
    if existing_device:
        saved_usn = existing_device['usn']
        session = datetime.now().strftime("%d-%m-%Y") + " (" + get_current_session() + ")"
        conn.close()
        return mark_attendance(saved_usn, session, device_id, token)

    if request.method == "POST":
        suffix = request.form.get("usn").strip().upper()
        password = request.form.get("password").strip()
        usn = f"1AM24EC{suffix}"

        c.execute('SELECT usn FROM Users WHERE usn = ? AND password = ?', (usn, password))
        valid_user = c.fetchone()
        
        if not valid_user:
            conn.close()
            return render_template_string(LOGIN_TEMPLATE, msg="❌ Invalid USN or password")

        # Check if another device is registered to this usn? Original CSV check handled that if device existed, 
        # but here the device_id didn't exist in the DB, so it's fresh.
        c.execute('INSERT INTO Devices (device_id, usn) VALUES (?, ?)', (device_id, usn))
        conn.commit()

        session = datetime.now().strftime("%d-%m-%Y") + " (" + get_current_session() + ")"
        conn.close()
        return mark_attendance(usn, session, device_id, token)
    
    conn.close()
    resp = make_response(render_template_string(LOGIN_TEMPLATE, msg=""))
    resp.set_cookie("device_id", device_id, max_age=31536000)
    return resp

@attendance_bp.route("/register", methods=["GET", "POST"])
def register():
    init_db()
    if request.method == "POST":
        suffix = request.form.get("usn").strip().upper()
        password = request.form.get("password").strip()
        usn = f"1AM24EC{suffix}"

        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT usn FROM Users WHERE usn = ?', (usn,))
        if c.fetchone():
            conn.close()
            return render_template_string(REGISTER_TEMPLATE, msg="⚠️ USN already registered.")

        c.execute('INSERT INTO Users (usn, password) VALUES (?, ?)', (usn, password))
        conn.commit()
        conn.close()
        return render_template_string(SUCCESS_TEMPLATE, message="✅ Registration successful. You can now log in.")

    return render_template_string(REGISTER_TEMPLATE, msg="")

def mark_attendance(usn, session, device_id, token):
    if "⚠️" in session or session == "No Ongoing Class":
        if token in active_tokens:
            del active_tokens[token]
        return make_response(render_template_string(
            SUCCESS_TEMPLATE, 
            message="❌ Not in class hours. Attendance blocked. Please contact your instructor if this is a mistake."
        ))

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id FROM Attendance WHERE usn = ? AND session = ? AND status = ?', (usn, session, 'P'))
    already_marked = c.fetchone()

    if not already_marked:
        c.execute('INSERT INTO Attendance (usn, session, status) VALUES (?, ?, ?)', (usn, session, 'P'))
        conn.commit()
        msg = f"✅ {usn} marked Present for {session}"
    else:
        msg = f"⚠️ {usn} already marked Present for {session}"
    
    conn.close()

    if token in active_tokens:
        del active_tokens[token]
        
    resp = make_response(render_template_string(SUCCESS_TEMPLATE, message=msg))
    resp.set_cookie("device_id", device_id, max_age=31536000)
    resp.set_cookie("user_usn", usn, max_age=31536000)
    return resp

@attendance_bp.route("/admin")
def admin():
    init_db()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM Attendance ORDER BY timestamp DESC')
    rows = c.fetchall()
    
    html = "<h2>Attendance Logs</h2><table border='1'><tr><th>USN</th><th>Session</th><th>Status</th><th>Timestamp</th></tr>"
    for row in rows:
        html += f"<tr><td>{row['usn']}</td><td>{row['session']}</td><td>{row['status']}</td><td>{row['timestamp']}</td></tr>"
    html += "</table>"
    conn.close()
    return html
