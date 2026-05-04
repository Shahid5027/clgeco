# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import qrcode
import os
import csv
from datetime import datetime, timedelta, time as dt_time
from io import BytesIO
import base64
import uuid
import json
import threading

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'your-secret-key-here')

# Hardcoded teacher credentials (override with env vars if desired)
TEACHER_USERNAME = os.environ.get('TEACHER_USERNAME', 'teacher')
TEACHER_PASSWORD = os.environ.get('TEACHER_PASSWORD', 'password123')

# Class prefix for roll numbers
ROLL_NUMBER_PREFIX = os.environ.get('ROLL_NUMBER_PREFIX', '1AM24EC')

# Class schedule (store times as "HH:MM" strings) - modify to match real schedule
CLASS_SCHEDULE = {
    1: {"start": "00:15", "end": "10:10", "name": "1st Hour"},
    2: {"start": "10:10", "end": "11:05", "name": "2nd Hour"},
    3: {"start": "11:20", "end": "12:15", "name": "3rd Hour"},
    4: {"start": "12:15", "end": "13:10", "name": "4th Hour"},
    5: {"start": "14:00", "end": "14:55", "name": "5th Hour"},
    6: {"start": "14:55", "end": "15:50", "name": "6th Hour"},
    7: {"start": "15:50", "end": "23:59", "name": "7th Hour"}
}

# QR code validity duration in seconds (adjust as needed)
QR_VALIDITY_SECONDS = int(os.environ.get('QR_VALIDITY_SECONDS', 5))

# In-memory QR session store and lock for thread-safety
active_qr_sessions = {}
active_qr_lock = threading.Lock()

# Filenames (can be changed)
USERS_CSV = 'users.csv'
ATTENDANCE_CSV = 'attendance.csv'


# -------------------------
# Utility & IO functions
# -------------------------
def init_csv_files():
    """Initialize CSV files if they don't exist (with headers)."""
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['roll_suffix', 'full_roll_number', 'registration_date'])

    if not os.path.exists(ATTENDANCE_CSV):
        with open(ATTENDANCE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['roll_number', 'date', 'hour', 'timestamp', 'session_id'])


def parse_time_str(tstr):
    """Parse 'HH:MM' -> datetime.time, returns None if invalid."""
    try:
        hh, mm = tstr.split(':')
        return dt_time(int(hh), int(mm))
    except Exception:
        return None


def get_current_class_hour():
    """Return current hour index (int) if within any scheduled hour, otherwise None."""
    now = datetime.now()
    now_time = now.time()

    for hour, sch in CLASS_SCHEDULE.items():
        start_t = parse_time_str(sch['start'])
        end_t = parse_time_str(sch['end'])
        if start_t is None or end_t is None:
            continue

        # Handle ranges that could cross midnight - assume end >= start for simplicity
        if start_t <= now_time <= end_t:
            return hour
    return None


def load_users():
    """Load users.csv into a DataFrame with safe defaults."""
    if os.path.exists(USERS_CSV):
        try:
            df = pd.read_csv(USERS_CSV, dtype=str)
            # Ensure headers exist
            expected_cols = ['roll_suffix', 'full_roll_number', 'registration_date']
            for c in expected_cols:
                if c not in df.columns:
                    df[c] = ''
            return df.fillna('')
        except Exception:
            return pd.DataFrame(columns=['roll_suffix', 'full_roll_number', 'registration_date'])
    return pd.DataFrame(columns=['roll_suffix', 'full_roll_number', 'registration_date'])


def save_user(roll_suffix):
    """Append a user to the users.csv"""
    full_roll_number = f"{ROLL_NUMBER_PREFIX}{roll_suffix}"
    registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([roll_suffix, full_roll_number, registration_date])


def load_attendance():
    """Load attendance.csv safely."""
    if os.path.exists(ATTENDANCE_CSV):
        try:
            df = pd.read_csv(ATTENDANCE_CSV, dtype=str)
            expected_cols = ['roll_number', 'date', 'hour', 'timestamp', 'session_id']
            for c in expected_cols:
                if c not in df.columns:
                    df[c] = ''
            return df.fillna('')
        except Exception:
            return pd.DataFrame(columns=['roll_number', 'date', 'hour', 'timestamp', 'session_id'])
    return pd.DataFrame(columns=['roll_number', 'date', 'hour', 'timestamp', 'session_id'])


def save_attendance(roll_number, hour, session_id):
    """Append attendance record."""
    date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ATTENDANCE_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([roll_number, date, str(hour), timestamp, session_id])


def generate_qr_code_base64(data_str):
    """Return data URI for QR PNG image representing data_str."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


# -------------------------
# Routes
# -------------------------
@app.route('/')
def index():
    return render_template('base.html')


@app.route('/teacher_login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()

        if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
            session.clear()
            session['user_type'] = 'teacher'
            session['username'] = username
            return redirect(url_for('teacher_dashboard'))
        else:
            return render_template('teacher_login.html', error='Invalid credentials')

    return render_template('teacher_login.html')


@app.route('/teacher_dashboard')
def teacher_dashboard():
    if session.get('user_type') != 'teacher':
        return redirect(url_for('teacher_login'))

    current_hour = get_current_class_hour()
    return render_template('teacher_dashboard.html', current_hour=current_hour, schedule=CLASS_SCHEDULE)


@app.route('/generate_qr', methods=['GET'])
def generate_qr():
    """Teacher-only endpoint to create a short-lived QR session and return QR PNG (base64)."""
    if session.get('user_type') != 'teacher':
        return redirect(url_for('teacher_login'))

    current_hour = get_current_class_hour()
    if not current_hour:
        return jsonify({'error': 'No active class hour'})

    session_id = str(uuid.uuid4())
    expiry_time = datetime.now() + timedelta(seconds=QR_VALIDITY_SECONDS)

    with active_qr_lock:
        # Save session info; use list for JSON-serializable used_by if later returned
        active_qr_sessions[session_id] = {
            'hour': int(current_hour),
            'expiry': expiry_time,
            'used_by': set()
        }

        # cleanup expired
        now = datetime.now()
        expired = [sid for sid, data in active_qr_sessions.items() if data['expiry'] < now]
        for sid in expired:
            del active_qr_sessions[sid]

    qr_payload = {
        'session_id': session_id,
        'hour': int(current_hour),
        'timestamp': datetime.now().isoformat()
    }
    qr_code_img = generate_qr_code_base64(json.dumps(qr_payload))

    return jsonify({
        'qr_code': qr_code_img,
        'session_id': session_id,
        'hour': int(current_hour),
        'expiry_time': expiry_time.isoformat(),
        'hour_name': CLASS_SCHEDULE[int(current_hour)]['name']
    })


@app.route('/student_register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        roll_suffix = (request.form.get('roll_suffix') or '').strip()

        # Validate: exactly 3 digits
        if not roll_suffix.isdigit() or len(roll_suffix) != 3:
            return render_template('register.html', error='Roll number suffix must be exactly 3 digits', prefix=ROLL_NUMBER_PREFIX)

        users_df = load_users()
        # ensure comparing strings
        if roll_suffix in users_df['roll_suffix'].astype(str).values:
            return render_template('register.html', error='Roll number already registered', prefix=ROLL_NUMBER_PREFIX)

        save_user(roll_suffix)
        return render_template('success.html', message='Registration successful! You can now login.')

    return render_template('register.html', prefix=ROLL_NUMBER_PREFIX)


@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_suffix = (request.form.get('roll_suffix') or '').strip()

        if not roll_suffix.isdigit() or len(roll_suffix) != 3:
            return render_template('student_login.html', error='Enter a valid 3-digit roll suffix', prefix=ROLL_NUMBER_PREFIX)

        users_df = load_users()
        if roll_suffix not in users_df['roll_suffix'].astype(str).values:
            return render_template('student_login.html', error='Roll number not found. Please register first.', prefix=ROLL_NUMBER_PREFIX)

        session.clear()
        session['user_type'] = 'student'
        session['roll_suffix'] = roll_suffix
        session['full_roll_number'] = f"{ROLL_NUMBER_PREFIX}{roll_suffix}"
        return redirect(url_for('qr_page'))

    return render_template('student_login.html', prefix=ROLL_NUMBER_PREFIX)


@app.route('/qr_page')
def qr_page():
    if session.get('user_type') != 'student':
        return redirect(url_for('student_login'))

    current_hour = get_current_class_hour()
    return render_template('qr_page.html',
                           current_hour=current_hour,
                           schedule=CLASS_SCHEDULE,
                           roll_number=session.get('full_roll_number'))


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        qr_data_str = request.form.get('qr_data')
        if not qr_data_str:
            return jsonify({'error': 'qr_data required'}), 400

        qr_data = json.loads(qr_data_str)
        session_id = qr_data.get('session_id')
        hour = int(qr_data.get('hour'))

        with active_qr_lock:
            if session_id not in active_qr_sessions:
                return jsonify({'error': 'Invalid or expired QR code'}), 400

            session_info = active_qr_sessions[session_id]

            # check expiry (session_info['expiry'] is datetime)
            if datetime.now() > session_info['expiry']:
                # cleanup
                del active_qr_sessions[session_id]
                return jsonify({'error': 'QR code has expired'}), 400

            roll_number = session.get('full_roll_number')
            if not roll_number:
                return jsonify({'error': 'Student not logged in'}), 401

            # prevent double marking for same QR session
            if roll_number in session_info['used_by']:
                return jsonify({'error': 'Attendance already marked for this session'}), 400

            # prevent marking for same hour today from CSV
            attendance_df = load_attendance()
            today = datetime.now().strftime("%Y-%m-%d")
            if len(attendance_df) > 0:
                existing = attendance_df[
                    (attendance_df['roll_number'] == roll_number) &
                    (attendance_df['date'] == today) &
                    (attendance_df['hour'].astype(str) == str(hour))
                ]
                if len(existing) > 0:
                    return jsonify({'error': 'Attendance already marked for this hour today'}), 400

            # mark attendance
            save_attendance(roll_number, hour, session_id)
            session_info['used_by'].add(roll_number)

        return jsonify({
            'success': True,
            'message': f'Attendance marked successfully for {CLASS_SCHEDULE.get(hour, {}).get("name", "Hour "+str(hour))}!'
        })

    except Exception as e:
        # don't leak internal traceback in production
        return jsonify({'error': f'Error processing attendance: {str(e)}'}), 500


@app.route('/admin')
def admin():
    if session.get('user_type') != 'teacher':
        return redirect(url_for('teacher_login'))

    users_df = load_users()
    attendance_df = load_attendance()
    today = datetime.now().strftime("%Y-%m-%d")

    if len(attendance_df) > 0:
        today_attendance = attendance_df[attendance_df['date'] == today]
    else:
        today_attendance = pd.DataFrame(columns=['roll_number', 'date', 'hour', 'timestamp', 'session_id'])

    attendance_data = {}
    for hour in range(1, len(CLASS_SCHEDULE) + 1):
        hour_attendance = today_attendance[today_attendance['hour'].astype(str) == str(hour)] if len(today_attendance) > 0 else pd.DataFrame()
        present_students = set(hour_attendance['roll_number'].tolist()) if len(hour_attendance) > 0 else set()

        all_students = []
        if len(users_df) > 0:
            for _, user in users_df.iterrows():
                roll_number = user['full_roll_number']
                status = 'P' if roll_number in present_students else 'A'
                all_students.append({
                    'roll_number': roll_number,
                    'status': status
                })

        all_students.sort(key=lambda x: x['roll_number'])
        attendance_data[hour] = {
            'students': all_students,
            'hour_name': CLASS_SCHEDULE.get(hour, {}).get('name', f'Hour {hour}'),
            'present_count': len(present_students),
            'total_count': len(all_students)
        }

    return render_template('admin.html',
                           attendance_data=attendance_data,
                           today=today)


@app.route('/attend_confirm')
def attend_confirm():
    if session.get('user_type') != 'student':
        return redirect(url_for('student_login'))
    return render_template('attend_confirm.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_csv_files()
    # debug=True only for development
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
