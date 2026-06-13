from flask import Flask, send_from_directory
from extensions import db
from flask_mail import Mail
from routes.auth import auth_bp
from routes.application import applications_bp
from routes.reminders import reminders_bp
from routes.events import events_bp
from routes.tools import tools_bp
from routes.jobs import jobs_bp
from routes.hr import hr_bp
from routes.vacancies import vacancies_bp

import os

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    os.makedirs(os.path.join(os.getcwd(), "templates", "hr"), exist_ok=True)

    app.config["SECRET_KEY"]                     = "jobtracker-secret-key-2025"
    app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///jobtracker.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"]                  = os.path.join(os.getcwd(), "uploads")
    app.config["MAX_CONTENT_LENGTH"]             = 5 * 1024 * 1024
    app.config["MEDIA_FOLDER"]                   = os.path.join(os.getcwd(), "media")
    app.config["HR_AVATAR_FOLDER"]               = os.path.join(os.getcwd(), "media", "hr_avatars")

    # ── ADD THIS LINE — use your PC's local IP ────────────────────────────────
    #app.config["SERVER_NAME"] = "192.168.1.44:5000"   # ← replace x.x with your actual IP

    # ── Brevo SMTP config ─────────────────────────────────────────────────────
    app.config["MAIL_SERVER"]         = "smtp-relay.brevo.com"
    app.config["MAIL_PORT"]           = 587
    app.config["MAIL_USE_TLS"]        = True
    app.config["MAIL_USE_SSL"]        = False
    app.config["MAIL_USERNAME"]       = "acca9d001@smtp-brevo.com"
    app.config["MAIL_PASSWORD"]       = "axYT9UmyQDp3srZN"
    app.config["MAIL_DEFAULT_SENDER"] = ("Job Tracker", "tartesamiksha@gmail.com")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["HR_AVATAR_FOLDER"], exist_ok=True)

    db.init_app(app)
    Mail(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(vacancies_bp)

    with app.app_context():
        db.create_all()

    @app.route("/media/hr_avatars/<path:filename>")
    def serve_hr_avatar(filename):
        return send_from_directory(app.config["HR_AVATAR_FOLDER"], filename)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)  # ← host changed to 0.0.0.0