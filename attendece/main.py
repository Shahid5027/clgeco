import qrcode
import pandas as pd
from flask import Flask, render_template_string, request, make_response, redirect
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import base64
from io import BytesIO
import uuid
import os

app = Flask(__name__)

attendance_file = "attendance.csv"
device_registry_file = "device_registry.csv"
users_file = "users.csv"
qr_expiry_seconds = 15
active_tokens = {}

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
<p>No account? <a href="/register">Register here</a></p>
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
<p>Already registered? <a href="/">Login</a></p>
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
@app.route("/")
def qr_page():
    cleanup_tokens()
    token = generate_qr_token()
    url = f"https://{request.host}/submit/{token}"
    qr_img = qrcode.make(url)
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return render_template_string(QR_TEMPLATE, qr=qr_str, expiry=qr_expiry_seconds)

@app.route("/submit/<token>", methods=["GET", "POST"])
def submit(token):
    cleanup_tokens()
    if token not in active_tokens:
        return render_template_string(SUCCESS_TEMPLATE, message="❌ QR Code expired or invalid.")

    device_id = get_device_id(request)
    usn_cookie = request.cookies.get("user_usn")

    if os.path.exists(device_registry_file):
        reg_df = pd.read_csv(device_registry_file)
    else:
        reg_df = pd.DataFrame(columns=["DeviceID", "USN"])

    existing = reg_df[reg_df["DeviceID"] == device_id]
    if not existing.empty:
        saved_usn = existing.iloc[0]["USN"]
        session = datetime.now().strftime("%d-%m") + " (" + get_current_session() + ")"
        return mark_attendance(saved_usn, session, device_id, token)

    if request.method == "POST":
        suffix = request.form.get("usn").strip().upper()
        password = request.form.get("password").strip()
        usn = f"1AM24EC{suffix}"

        if os.path.exists(users_file):
            users_df = pd.read_csv(users_file)
            valid_user = users_df[(users_df["USN"] == usn) & (users_df["Password"] == password)]
            if valid_user.empty:
                return render_template_string(LOGIN_TEMPLATE, msg="❌ Invalid USN or password")
        else:
            return render_template_string(LOGIN_TEMPLATE, msg="❌ Users file not found")

        existing = reg_df[reg_df["DeviceID"] == device_id]
        if not existing.empty and existing.iloc[0]["USN"] != usn:
            return render_template_string(SUCCESS_TEMPLATE, message=f"❌ Device already linked to {existing.iloc[0]['USN']}")

        reg_df = pd.concat([reg_df, pd.DataFrame([[device_id, usn]], columns=["DeviceID", "USN"])]).drop_duplicates()
        reg_df.to_csv(device_registry_file, index=False)

        session = datetime.now().strftime("%d-%m") + " (" + get_current_session() + ")"
        return mark_attendance(usn, session, device_id, token)

    resp = make_response(render_template_string(LOGIN_TEMPLATE, msg=""))
    resp.set_cookie("device_id", device_id, max_age=31536000)
    return resp

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        suffix = request.form.get("usn").strip().upper()
        password = request.form.get("password").strip()
        usn = f"1AM24EC{suffix}"

        if os.path.exists(users_file):
            users_df = pd.read_csv(users_file)
        else:
            users_df = pd.DataFrame(columns=["USN", "Password"])

        if usn in users_df["USN"].values:
            return render_template_string(REGISTER_TEMPLATE, msg="⚠️ USN already registered.")

        users_df = pd.concat([users_df, pd.DataFrame([[usn, password]], columns=["USN", "Password"])])
        users_df.to_csv(users_file, index=False)
        return render_template_string(SUCCESS_TEMPLATE, message="✅ Registration successful. You can now log in.")

    return render_template_string(REGISTER_TEMPLATE, msg="")

def mark_attendance(usn, session, device_id, token):
    if "⚠️" in session or session == "No Ongoing Class":
        del active_tokens[token]
        return make_response(render_template_string(
            SUCCESS_TEMPLATE, 
            message="❌ Not in class hours. Attendance blocked. Please contact your instructor if this is a mistake."
        ))

    try:
        df = pd.read_csv(attendance_file)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["USN"])

    if usn not in df["USN"].values:
        df = pd.concat([df, pd.DataFrame([[usn]], columns=["USN"])])

    if session not in df.columns:
        df[session] = 'A'

    already_marked = df.loc[df["USN"] == usn, session].values[0] == 'P'

    if not already_marked:
        df.loc[df["USN"] == usn, session] = 'P'
        df = df.sort_values("USN")
        df.to_csv(attendance_file, index=False)
        msg = f"✅ {usn} marked Present for {session}"
    else:
        msg = f"⚠️ {usn} already marked Present for {session}"

    del active_tokens[token]
    resp = make_response(render_template_string(SUCCESS_TEMPLATE, message=msg))
    resp.set_cookie("device_id", device_id, max_age=31536000)
    resp.set_cookie("user_usn", usn, max_age=31536000)
    return resp

@app.route("/admin")
def admin():
    if not os.path.exists(attendance_file):
        return "No attendance data yet."
    df = pd.read_csv(attendance_file)
    return df.to_html(index=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)