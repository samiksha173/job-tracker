from flask import Flask
from extensions import db
from routes.auth import auth_bp
from routes.application import applications_bp
from routes.reminders import reminders_bp
from routes.events import events_bp
from routes.tools import tools_bp
from routes.jobs import jobs_bp
from routes.hr import hr_bp

import os

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ensure HR template subfolder exists
    os.makedirs(os.path.join(os.getcwd(), "templates", "hr"), exist_ok=True)

    # ── Core config ────────────────────────────────────────────────────────────
    app.config["SECRET_KEY"]                  = "jobtracker-secret-key-2025"
    app.config["SQLALCHEMY_DATABASE_URI"]     = "sqlite:///jobtracker.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"]               = os.path.join(os.getcwd(), "uploads")
    app.config["MAX_CONTENT_LENGTH"]          = 5 * 1024 * 1024  # 5 MB

    # ── Flask-Mail config ──────────────────────────────────────────────────────
    # Using Gmail SMTP. Replace the two values below with your Gmail address
    # and an App Password (NOT your normal Gmail password).
    #
    # How to get a Gmail App Password:
    #   1. Go to myaccount.google.com → Security
    #   2. Enable 2-Step Verification (required)
    #   3. Search "App passwords" → create one for "Mail"
    #   4. Paste the 16-character code below
    #
    app.config["MAIL_SERVER"]         = "smtp.gmail.com"
    app.config["MAIL_PORT"]           = 587
    app.config["MAIL_USE_TLS"]        = True
    app.config["MAIL_USE_SSL"]        = False
    app.config["MAIL_USERNAME"]       = "your_gmail@gmail.com"      # ← change this
    app.config["MAIL_PASSWORD"]       = "your_app_password_here"    # ← change this
    app.config["MAIL_DEFAULT_SENDER"] = ("Job Tracker", "your_gmail@gmail.com")  # ← change this

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(hr_bp)

    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)