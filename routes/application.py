from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template, current_app, send_from_directory
from werkzeug.utils import secure_filename
from models import Application
from extensions import db
from datetime import date
import os, json

applications_bp = Blueprint("applications", __name__)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

# ── Page routes ─────────────────────────────────────────────────────────────

@applications_bp.route("/application")
def application_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("application.html")

# ── API: list / create ───────────────────────────────────────────────────────

@applications_bp.route("/api/applications", methods=["GET"])
def list_applications():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    include_deleted = request.args.get("deleted", "false") == "true"
    query = Application.query.filter_by(user_id=uid)
    if not include_deleted:
        query = query.filter_by(deleted=False)
    apps = query.order_by(Application.created_at.desc()).all()
    return jsonify([a.to_dict() for a in apps])

@applications_bp.route("/api/applications", methods=["POST"])
def create_application():
    err = login_required()
    if err: return err
    uid = session["user_id"]

    # Handle multipart (with file) or JSON
    def field(name, default=""):
        return request.form.get(name, default) if request.content_type and "multipart" in request.content_type else (request.get_json() or {}).get(name, default)

    def parse_date(val):
        try:
            return date.fromisoformat(val) if val else None
        except Exception:
            return None

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
        application_date=parse_date(field("application_date")),
        deadline=parse_date(field("deadline")),
        interview_date=parse_date(field("interview_date")),
        resume_filename=resume_filename,
        job_description=field("job_description"),
        notes=field("notes"),
        contact_person=field("contact_person"),
        contact_email=field("contact_email"),
        job_url=field("job_url"),
    )
    db.session.add(app)
    db.session.commit()
    return jsonify(app.to_dict()), 201

# ── API: single get / update / delete ────────────────────────────────────────

@applications_bp.route("/api/applications/<int:app_id>", methods=["GET"])
def get_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    return jsonify(a.to_dict())

@applications_bp.route("/api/applications/<int:app_id>", methods=["PUT"])
def update_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    data = request.get_json() or {}

    def parse_date(val):
        try:
            return date.fromisoformat(val) if val else None
        except Exception:
            return None

    for field in ["company", "position", "status", "job_type", "location", "salary",
                  "job_description", "notes", "contact_person", "contact_email", "job_url"]:
        if field in data:
            setattr(a, field, data[field])
    for df in ["application_date", "deadline", "interview_date"]:
        if df in data:
            setattr(a, df, parse_date(data[df]))
    db.session.commit()
    return jsonify(a.to_dict())

@applications_bp.route("/api/applications/<int:app_id>", methods=["DELETE"])
def delete_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    a.deleted = True          # soft delete → recycle bin
    db.session.commit()
    return jsonify({"success": True})

@applications_bp.route("/api/applications/<int:app_id>/restore", methods=["POST"])
def restore_application(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    a.deleted = False
    db.session.commit()
    return jsonify({"success": True})

@applications_bp.route("/api/applications/<int:app_id>/permanent", methods=["DELETE"])
def permanent_delete(app_id):
    err = login_required()
    if err: return err
    a = Application.query.filter_by(id=app_id, user_id=session["user_id"]).first_or_404()
    db.session.delete(a)
    db.session.commit()
    return jsonify({"success": True})

# ── Stats for dashboard ───────────────────────────────────────────────────────

@applications_bp.route("/api/applications/stats", methods=["GET"])
def stats():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=False).all()
    today = date.today()
    from datetime import timedelta
    soon = today + timedelta(days=7)
    return jsonify({
        "total": len(apps),
        "applied": sum(1 for a in apps if a.status == "Applied"),
        "interview": sum(1 for a in apps if a.status == "Interview"),
        "offer": sum(1 for a in apps if a.status == "Offer"),
        "rejected": sum(1 for a in apps if a.status == "Rejected"),
        "upcoming_deadlines": sum(1 for a in apps if a.deadline and today <= a.deadline <= soon),
        "upcoming_interviews": sum(1 for a in apps if a.interview_date and today <= a.interview_date <= soon),
    })

# ── Resume download ───────────────────────────────────────────────────────────

@applications_bp.route("/api/resume/<filename>")
def get_resume(filename):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

# ── Export / Import ───────────────────────────────────────────────────────────

@applications_bp.route("/api/applications/export", methods=["GET"])
def export_data():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=False).all()
    data = [a.to_dict() for a in apps]
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
            def pd(val):
                try: return date.fromisoformat(val) if val else None
                except: return None
            a = Application(
                user_id=uid,
                company=r.get("company", ""),
                position=r.get("position", ""),
                status=r.get("status", "Applied"),
                job_type=r.get("job_type", ""),
                location=r.get("location", ""),
                salary=r.get("salary", ""),
                application_date=pd(r.get("application_date")),
                deadline=pd(r.get("deadline")),
                interview_date=pd(r.get("interview_date")),
                job_description=r.get("job_description", ""),
                notes=r.get("notes", ""),
                contact_person=r.get("contact_person", ""),
                contact_email=r.get("contact_email", ""),
                job_url=r.get("job_url", ""),
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
    uid = session["user_id"]
    Application.query.filter_by(user_id=uid).delete()
    db.session.commit()
    return jsonify({"success": True})