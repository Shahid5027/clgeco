from flask import Flask, render_template

from routes.study_api import study_bp
from routes.attendance_api import attendance_bp

app = Flask(__name__)
# Configurations from study app
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Register Blueprints
app.register_blueprint(study_bp, url_prefix='/study')
app.register_blueprint(attendance_bp, url_prefix='/attendance')

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/notes')
def notes():
    return render_template('notes.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
