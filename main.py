from flask import Flask, render_template, request, session, redirect, url_for

from routes.study_api import study_bp
from routes.attendance_api import attendance_bp
from routes.auth_api import auth_bp

app = Flask(__name__)
# Configurations
app.secret_key = 'super_secret_key_campus'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(study_bp, url_prefix='/study')
app.register_blueprint(attendance_bp, url_prefix='/attendance')

@app.before_request
def require_login():
    allowed_endpoints = ['auth.login', 'static']
    
    if request.endpoint not in allowed_endpoints and not request.path.startswith('/static'):
        if not session.get('role'):
            return redirect(url_for('auth.login'))

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/notes')
def notes():
    return render_template('notes.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
