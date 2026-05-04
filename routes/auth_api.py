from flask import Blueprint, render_template, request, session, redirect, url_for

auth_bp = Blueprint('auth', __name__)

STUDENT_PASSWORD = 'student123'
FACULTY_CREDENTIALS = {'faculty@amcec.edu': 'faculty123'}
ADMIN_CREDENTIALS = {'admin@amcec.edu': 'admin123'}

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')

        # Check Admin
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
            session['role'] = 'admin'
            session['id'] = username
            return redirect(url_for('index'))
            
        # Check Faculty
        if username in FACULTY_CREDENTIALS and FACULTY_CREDENTIALS[username] == password:
            session['role'] = 'faculty'
            session['id'] = username
            return redirect(url_for('index'))

        # Check Student (expecting last 3 digits e.g. 143)
        if username.isdigit() and len(username) == 3:
            if password == STUDENT_PASSWORD:
                session['role'] = 'student'
                session['id'] = f"1am24ec{username}"
                return redirect(url_for('index'))
                
        error = "Invalid credentials. Please verify your login details."
        return render_template('login.html', error=error)
        
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
