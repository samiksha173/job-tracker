
from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template, current_app, send_from_directory
from werkzeug.utils import secure_filename
from sqlalchemy import inspect, text
from models import Application, notify_all_hr_users
from extensions import db
from datetime import date
import os, json

applications_bp = Blueprint("applications", __name__)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def ensure_deleted_column():
    inspector = inspect(db.engine)
    cols = [c["name"] for c in inspector.get_columns("application")]
    if "deleted" not in cols:
        db.session.execute(text("ALTER TABLE application ADD COLUMN deleted BOOLEAN DEFAULT 0"))
        db.session.commit()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

def application_to_dict(a):
    return {
        "id": a.id,
        "user_id": a.user_id,
        "company": a.company or "",
        "position": a.position or "",
        "status": a.status or "Applied",
        "application_date": a.application_date or "",
        "deadline": a.deadline or "",
        "interview_date": a.interview_datetime or "",
        "interview_datetime": a.interview_datetime or "",
        "location": a.location or "",
        "job_type": a.job_type or "",
        "salary": a.salary or "",
        "job_description": a.job_description or "",
        "notes": a.notes or "",
        "resume_filename": a.resume_filename or "",
        "hr_status": a.hr_status or "Pending",
        "hr_notes": a.hr_notes or "",
        "deleted": bool(getattr(a, "deleted", False)),
    }

@applications_bp.route("/application")
def application_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("application.html")

@applications_bp.route("/api/applications", methods=["GET"])
def list_applications():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=False).order_by(Application.id.desc()).all()
    return jsonify([application_to_dict(a) for a in apps])

@applications_bp.route("/api/applications", methods=["POST"])
def create_application():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]

    def field(name, default=""):
        return request.form.get(name, default) if request.content_type and "multipart" in request.content_type else (request.get_json() or {}).get(name, default)

    resume_filename = None
    if "resume" in request.files:
        f = request.files["resume"]
        if f and allowed_file(f.filename):
            fn = secure_filename(f.filename)
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], fn)
            f.save(save_path)
            resume_filename = fn

    app = Application(
        user_id=uid,
        company=field("company"),
        position=field("position"),
        status=field("status", "Applied"),
        job_type=field("job_type"),
        location=field("location"),
        salary=field("salary"),
        application_date=field("application_date"),
        deadline=field("deadline"),
        interview_datetime=field("interview_date"),
        resume_filename=resume_filename,
        job_description=field("job_description"),
        notes=field("notes"),
    )
    db.session.add(app)
    db.session.commit()

    notify_all_hr_users(
        "new_application_received",
        f"New application received for {app.position} at {app.company}.",
        related_application=app.id,
    )

    return jsonify(application_to_dict(app)), 201

@applications_bp.route("/api/applications/<int:app_id>", methods=["GET"])
def get_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    return jsonify(application_to_dict(a))

@applications_bp.route("/api/applications/<int:app_id>", methods=["PUT"])
def update_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    data = request.get_json() or {}

    for field in ["company", "position", "status", "job_type", "location", "salary",
                  "job_description", "notes"]:
        if field in data:
            setattr(a, field, data[field])

    for df in ["application_date", "deadline"]:
        if df in data:
            setattr(a, df, data[df])

    if "interview_date" in data:
        a.interview_datetime = data["interview_date"]
    if "interview_datetime" in data:
        a.interview_datetime = data["interview_datetime"]

    db.session.commit()
    return jsonify(application_to_dict(a))

@applications_bp.route("/api/applications/<int:app_id>", methods=["DELETE"])
def delete_application(app_id):
    err = login_required()
    if err: return err
    ensure_deleted_column()
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    a.deleted = True
    db.session.commit()
    return jsonify({"success": True})

@applications_bp.route("/api/applications/<int:app_id>/restore", methods=["POST"])
def restore_application(app_id):
    err = login_required()
    if err: return err
    ensure_deleted_column()
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    a.deleted = False
    db.session.commit()
    return jsonify({"success": True})

@applications_bp.route("/api/applications/<int:app_id>/permanent", methods=["DELETE"])
def permanent_delete(app_id):
    err = login_required()
    if err: return err
    ensure_deleted_column()
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True})

@applications_bp.route("/api/applications/stats", methods=["GET"])
def stats():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=False).all()
    today = date.today()

    from datetime import timedelta
    soon = today + timedelta(days=7)

    def as_date(val):
        try:
            return date.fromisoformat(val) if val else None
        except Exception:
            return None

    return jsonify({
        "total": len(apps),
        "applied": sum(1 for a in apps if a.status == "Applied"),
        "interview": sum(1 for a in apps if a.status == "Interview"),
        "offer": sum(1 for a in apps if a.status == "Offer"),
        "rejected": sum(1 for a in apps if a.status == "Rejected"),
        "upcoming_deadlines": sum(1 for a in apps if as_date(a.deadline) and today <= as_date(a.deadline) <= soon),
        "upcoming_interviews": sum(1 for a in apps if as_date(a.interview_datetime) and today <= as_date(a.interview_datetime) <= soon),
    })

@applications_bp.route("/api/resume/<filename>")
def get_resume(filename):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

@applications_bp.route("/api/applications/export", methods=["GET"])
def export_data():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=False).all()
    data = [application_to_dict(a) for a in apps]

    from flask import Response
    return Response(
        json.dumps(data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=job_applications.json"}
    )

@applications_bp.route("/api/applications/import", methods=["POST"])
def import_data():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        records = json.load(file)
        count = 0

        for r in records:
            a = Application(
                user_id=uid,
                company=r.get("company", ""),
                position=r.get("position", ""),
                status=r.get("status", "Applied"),
                job_type=r.get("job_type", ""),
                location=r.get("location", ""),
                salary=r.get("salary", ""),
                application_date=r.get("application_date", ""),
                deadline=r.get("deadline", ""),
                interview_datetime=r.get("interview_date", ""),
                job_description=r.get("job_description", ""),
                notes=r.get("notes", ""),
            )
            db.session.add(a)
            count += 1

        db.session.commit()
        return jsonify({"success": True, "imported": count})

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@applications_bp.route("/api/applications/clear", methods=["DELETE"])
def clear_all():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    Application.query.filter_by(user_id=uid).delete()
    db.session.commit()
    return jsonify({"success": True})
