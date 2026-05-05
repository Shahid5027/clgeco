from flask import Flask, render_template, render_template_string

from routes.study_api import study_bp
from routes.attendance_api import attendance_bp

app = Flask(__name__)
app.register_blueprint(study_bp, url_prefix="/study")
app.register_blueprint(attendance_bp, url_prefix="/attendance")


@app.route("/")
def home():
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>College Ecosystem</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 2rem; }
                ul { line-height: 2; }
            </style>
        </head>
        <body>
            <h1>College Ecosystem</h1>
            <p>Select a module:</p>
            <ul>
                <li><a href="/study/">Study</a></li>
                <li><a href="/attendance/">Attendance</a></li>
                <li><a href="/notes">Notes</a></li>
            </ul>
        </body>
        </html>
        """
    )


@app.route("/notes")
def notes():
    return render_template("notes.html")


if __name__ == "__main__":
    app.run(debug=True)
