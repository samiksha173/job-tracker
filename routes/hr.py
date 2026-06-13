import os
import uuid
from datetime import datetime

from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Application, Message, Notification, UserProfile, create_notification, notify_all_hr_users, sync_vacancy_deadline_notifications, JobVacancy
from functools import wraps

hr_bp = Blueprint("hr", __name__, url_prefix="/hr")


def hr_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "hr":
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def get_hr_context():
    user = User.query.get(session["user_id"])
    profile = UserProfile.query.filter_by(user_id=user.id).first() if user else None
    return {"user": user, "profile": profile}


# ── Pages ─────────────────────────────────────────────────────────────────────

@hr_bp.route("/dashboard")
@hr_required
def hr_dashboard():
    context = get_hr_context()
    return render_template("hr/dashboard.html", active="hr_dashboard", **context)


@hr_bp.route("/applications")
@hr_required
def hr_applications():
    context = get_hr_context()
    return render_template("hr/applications.html", active="hr_applications", **context)


@hr_bp.route("/applicants")
@hr_required
def hr_applicants():
    context = get_hr_context()
    return render_template("hr/applicants.html", active="hr_applicants", **context)


# ── NEW: Vacancies management page ────────────────────────────────────────────
@hr_bp.route("/vacancies")
@hr_required
def hr_vacancies_page():
    context = get_hr_context()
    return render_template("hr/vacancies.html", active="hr_vacancies", **context)


@hr_bp.route("/profile", methods=["GET", "POST"])
@hr_required
def hr_profile():
    user = User.query.get(session["user_id"])
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        errors = []
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        user.name = request.form.get("full_name", "").strip() or user.name
        user.company = request.form.get("company_name", "").strip() or user.company
        profile.job_title = request.form.get("job_title", "").strip()
        profile.company_website = request.form.get("company_website", "").strip()
        profile.phone_number = request.form.get("phone_number", "").strip()
        profile.work_email = request.form.get("work_email", "").strip()
        profile.linkedin_url = request.form.get("linkedin_url", "").strip()
        profile.location = request.form.get("location", "").strip()
        profile.bio = request.form.get("bio", "").strip()
        profile.email_notifications = request.form.get("email_notifications") == "on"

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            if not avatar_file.mimetype.startswith("image/"):
                errors.append("Avatar must be an image file.")
            else:
                avatar_dir = current_app.config["HR_AVATAR_FOLDER"]
                os.makedirs(avatar_dir, exist_ok=True)
                safe_name = secure_filename(avatar_file.filename)
                unique_name = f"{user.id}_{uuid.uuid4().hex}_{safe_name}"
                avatar_path = os.path.join(avatar_dir, unique_name)
                avatar_file.save(avatar_path)

                if profile.avatar_filename:
                    old_path = os.path.join(avatar_dir, profile.avatar_filename)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                profile.avatar_filename = unique_name

        if new_password or confirm_password or current_password:
            if not check_password_hash(user.password, current_password):
                errors.append("Current password is incorrect.")
            if new_password != confirm_password:
                errors.append("New password and confirmation do not match.")
            if len(new_password) < 8:
                errors.append("New password must be at least 8 characters long.")
            if not errors:
                user.password = generate_password_hash(new_password)

        profile.updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if not profile.created_at:
            profile.created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        db.session.commit()
        session["user_name"] = user.name

        total_vacancies = JobVacancy.query.filter_by(posted_by=user.id).count()
        reviewed_applications = Application.query.filter(
            Application.position.in_([vac.title for vac in JobVacancy.query.filter_by(posted_by=user.id).all()]),
            Application.company == user.company,
            Application.hr_status != "Pending"
        ).count()

        success_message = "Profile updated successfully"
        if errors:
            return render_template(
                "hr/profile.html",
                active="hr_profile",
                user=user,
                profile=profile,
                total_vacancies=total_vacancies,
                reviewed_applications=reviewed_applications,
                success_message=None,
                errors=errors,
            )

        return render_template(
            "hr/profile.html",
            active="hr_profile",
            user=user,
            profile=profile,
            total_vacancies=total_vacancies,
            reviewed_applications=reviewed_applications,
            success_message=success_message,
            errors=[],
        )

    total_vacancies = JobVacancy.query.filter_by(posted_by=user.id).count()
    reviewed_applications = Application.query.filter(
        Application.position.in_([vac.title for vac in JobVacancy.query.filter_by(posted_by=user.id).all()]),
        Application.company == user.company,
        Application.hr_status != "Pending"
    ).count()

    return render_template(
        "hr/profile.html",
        active="hr_profile",
        user=user,
        profile=profile,
        total_vacancies=total_vacancies,
        reviewed_applications=reviewed_applications,
        success_message=None,
        errors=[],
    )


# ── API ───────────────────────────────────────────────────────────────────────

NOTIFICATION_META = {
    "new_application_received": {
        "title": "New application received",
        "icon": "📥",
    },
    "application_status_changed": {
        "title": "Application status changed",
        "icon": "🔄",
    },
    "vacancy_deadline_approaching": {
        "title": "Vacancy deadline approaching",
        "icon": "⏰",
    },
    "vacancy_expired": {
        "title": "Vacancy expired",
        "icon": "⚠️",
    },
}


@hr_bp.route("/api/notifications")
@hr_required
def hr_get_notifications():
    sync_vacancy_deadline_notifications()
    notifications = (
        Notification.query
        .filter_by(hr_user=session["user_id"])
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .all()
    )

    payload = []
    for note in notifications:
        meta = NOTIFICATION_META.get(note.type, {"title": "Notification", "icon": "🔔"})
        payload.append({
            "id": note.id,
            "type": note.type,
            "title": meta["title"],
            "icon": meta["icon"],
            "message": note.message,
            "is_read": note.is_read,
            "created_at": note.created_at,
            "relative_time": note.to_dict()["relative_time"],
            "related_application": note.related_application,
            "related_vacancy": note.related_vacancy,
        })
    return jsonify(payload)


@hr_bp.route("/api/notifications/<int:note_id>/read", methods=["POST"])
@hr_required
def hr_mark_notification_read(note_id):
    note = Notification.query.filter_by(id=note_id, hr_user=session["user_id"]).first_or_404()
    note.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@hr_bp.route("/api/notifications/read-all", methods=["POST"])
@hr_required
def hr_mark_all_notifications_read():
    Notification.query.filter_by(hr_user=session["user_id"], is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})


@hr_bp.route("/api/stats")
@hr_required
def hr_stats():
    apps = Application.query.all()
    total     = len(apps)
    pending   = sum(1 for a in apps if (a.hr_status or "Pending") == "Pending")
    interview = sum(1 for a in apps if a.hr_status == "Interview")
    hired     = sum(1 for a in apps if a.hr_status == "Hired")
    eligible  = sum(1 for a in apps if a.hr_status == "Eligible")
    rejected  = sum(1 for a in apps if a.hr_status == "Rejected")
    not_elig  = sum(1 for a in apps if a.hr_status == "Not Eligible")
    total_applicants = User.query.filter_by(role="applicant").count()
    return jsonify({
        "total": total, "pending": pending, "interview": interview,
        "hired": hired, "eligible": eligible,
        "rejected": rejected, "not_eligible": not_elig,
        "total_applicants": total_applicants
    })


@hr_bp.route("/api/applications")
@hr_required
def hr_get_applications():
    search    = request.args.get("search", "").lower()
    hr_status = request.args.get("hr_status", "")
    position  = request.args.get("position", "")

    query = Application.query
    apps  = query.order_by(Application.id.desc()).all()

    result = []
    for a in apps:
        user = User.query.get(a.user_id)
        d = {
            "id":               a.id,
            "applicant_name":   user.name  if user else "—",
            "applicant_email":  user.email if user else "—",
            "company":          a.company,
            "position":         a.position,
            "status":           a.status,
            "hr_status":        a.hr_status or "Pending",
            "hr_notes":         a.hr_notes or "",
            "interview_datetime": a.interview_datetime or "",
            "application_date": a.application_date or "",
            "location":         a.location or "",
            "job_type":         a.job_type or "",
            "salary":           a.salary or "",
            "job_description":  a.job_description or "",
            "notes":            a.notes or "",
            "resume_filename":  a.resume_filename or "",
        }
        if search and search not in d["applicant_name"].lower() and \
                      search not in d["position"].lower() and \
                      search not in d["company"].lower():
            continue
        if hr_status and d["hr_status"] != hr_status:
            continue
        if position and d["position"] != position:
            continue
        result.append(d)
    return jsonify(result)


@hr_bp.route("/api/applications/<int:app_id>/review", methods=["POST"])
@hr_required
def hr_review_application(app_id):
    a    = Application.query.get_or_404(app_id)
    data = request.get_json() or {}
    old_status = a.hr_status
    if "hr_status"          in data: a.hr_status           = data["hr_status"]
    if "hr_notes"           in data: a.hr_notes            = data["hr_notes"]
    if "interview_datetime" in data: a.interview_datetime  = data["interview_datetime"]
    db.session.commit()

    new_status = a.hr_status
    if new_status != old_status:
        notify_all_hr_users(
            "application_status_changed",
            f"Application #{a.id} for {a.position} at {a.company} status changed to {new_status}.",
            related_application=a.id,
        )

    return jsonify({"success": True})


@hr_bp.route("/api/positions")
@hr_required
def hr_positions():
    apps = Application.query.with_entities(Application.position).distinct().all()
    return jsonify([a.position for a in apps if a.position])


@hr_bp.route("/api/applicants")
@hr_required
def hr_get_applicants():
    users = User.query.filter_by(role="applicant").all()
    result = []
    for u in users:
        apps     = Application.query.filter_by(user_id=u.id).all()
        statuses = list({a.hr_status or "Pending" for a in apps})
        result.append({
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "total_apps": len(apps),
            "statuses":   statuses,
            "joined":     str(u.id),
        })
    return jsonify(result)


@hr_bp.route("/api/applications/<int:app_id>/messages", methods=["GET"])
@hr_required
def get_messages(app_id):
    msgs = Message.query.filter_by(application_id=app_id).order_by(Message.id).all()
    return jsonify([{"sender": m.sender, "message": m.message, "sent_at": m.sent_at} for m in msgs])


@hr_bp.route("/api/applications/<int:app_id>/messages", methods=["POST"])
@hr_required
def post_message(app_id):
    data = request.get_json() or {}
    msg  = Message(application_id=app_id, sender=data.get("sender", "hr"),
                   message=data.get("message", ""))
    db.session.add(msg)
    db.session.commit()
    return jsonify({"success": True})