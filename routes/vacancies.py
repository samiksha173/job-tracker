from flask import Blueprint, request, jsonify, session
from models import db, notify_all_hr_users
from functools import wraps

vacancies_bp = Blueprint("vacancies", __name__)

def hr_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "hr":
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Get all vacancies (public — applicants can see) ────────────────────────────
@vacancies_bp.route("/api/vacancies", methods=["GET"])
def get_vacancies():
    from models import JobVacancy
    vacs = JobVacancy.query.filter_by(is_active=True).order_by(JobVacancy.created_at.desc()).all()
    return jsonify([v.to_dict() for v in vacs])


# ── HR: get all their own vacancies ───────────────────────────────────────────
@vacancies_bp.route("/hr/api/vacancies", methods=["GET"])
@hr_required
def hr_get_vacancies():
    from models import JobVacancy
    vacs = JobVacancy.query.filter_by(posted_by=session["user_id"]).order_by(JobVacancy.created_at.desc()).all()
    return jsonify([v.to_dict() for v in vacs])


# ── HR: create vacancy ────────────────────────────────────────────────────────
@vacancies_bp.route("/hr/api/vacancies", methods=["POST"])
@hr_required
def hr_create_vacancy():
    from models import JobVacancy, User
    data = request.get_json() or {}

    hr_user = User.query.get(session["user_id"])
    company = hr_user.company if hr_user and hr_user.company else data.get("company", "")

    vac = JobVacancy(
        title=data.get("title", "").strip(),
        company=company or data.get("company", "").strip(),
        location=data.get("location", "").strip(),
        job_type=data.get("job_type", "Full-time"),
        experience=data.get("experience", "").strip(),
        salary=data.get("salary", "").strip(),
        description=data.get("description", "").strip(),
        requirements=data.get("requirements", "").strip(),
        skills=data.get("skills", "").strip(),
        deadline=data.get("deadline", None),
        is_active=True,
        posted_by=session["user_id"]
    )
    db.session.add(vac)
    db.session.commit()
    return jsonify({"success": True, "vacancy": vac.to_dict()})


# ── HR: update vacancy ────────────────────────────────────────────────────────
@vacancies_bp.route("/hr/api/vacancies/<int:vid>", methods=["PUT"])
@hr_required
def hr_update_vacancy(vid):
    from models import JobVacancy
    vac = JobVacancy.query.filter_by(id=vid, posted_by=session["user_id"]).first_or_404()
    data = request.get_json() or {}
    for field in ["title", "company", "location", "job_type", "experience",
                  "salary", "description", "requirements", "skills", "deadline"]:
        if field in data:
            setattr(vac, field, data[field])
    if "is_active" in data:
        vac.is_active = data["is_active"]
    db.session.commit()
    return jsonify({"success": True, "vacancy": vac.to_dict()})


# ── HR: get vacancy detail with applicants ────────────────────────────────────
@vacancies_bp.route("/hr/api/vacancies/<int:vid>/detail", methods=["GET"])
@hr_required
def hr_get_vacancy_detail(vid):
    from models import Application, JobVacancy, User

    vac = JobVacancy.query.filter_by(id=vid, posted_by=session["user_id"]).first_or_404()
    applications = (
        Application.query
        .filter_by(company=vac.company, position=vac.title)
        .order_by(Application.id.desc())
        .all()
    )

    applicant_rows = []
    for app in applications:
        user = User.query.get(app.user_id)
        applicant_rows.append({
            "id": app.id,
            "name": user.name if user else "Unknown Applicant",
            "email": user.email if user else "unknown@example.com",
            "applied_date": app.application_date or "—",
            "hr_status": app.hr_status or "Pending",
            "status": app.status or "Applied",
        })

    summary = {
        "total_applied": len(applicant_rows),
        "pending": sum(1 for app in applicant_rows if (app["hr_status"] or "Pending") == "Pending"),
        "interview": sum(1 for app in applicant_rows if app["hr_status"] == "Interview"),
        "hired": sum(1 for app in applicant_rows if app["hr_status"] == "Hired"),
        "rejected": sum(1 for app in applicant_rows if app["hr_status"] == "Rejected"),
    }

    return jsonify({
        "vacancy": vac.to_dict(),
        "applicants": applicant_rows,
        "summary": summary,
    })


# ── HR: delete vacancy ────────────────────────────────────────────────────────
@vacancies_bp.route("/hr/api/vacancies/<int:vid>", methods=["DELETE"])
@hr_required
def hr_delete_vacancy(vid):
    from models import JobVacancy
    vac = JobVacancy.query.filter_by(id=vid, posted_by=session["user_id"]).first_or_404()
    db.session.delete(vac)
    db.session.commit()
    return jsonify({"success": True})


# ── Applicant: apply to vacancy ───────────────────────────────────────────────
@vacancies_bp.route("/api/vacancies/<int:vid>/apply", methods=["POST"])
def apply_vacancy(vid):
    if "user_id" not in session or session.get("role") != "applicant":
        return jsonify({"error": "Login as applicant first"}), 401
    from models import JobVacancy, Application
    import datetime
    vac = JobVacancy.query.get_or_404(vid)
    # Check already applied
    existing = Application.query.filter_by(
        user_id=session["user_id"], position=vac.title, company=vac.company
    ).first()
    if existing:
        return jsonify({"success": False, "message": "You have already applied for this position."})
    app = Application(
        user_id=session["user_id"],
        company=vac.company,
        position=vac.title,
        location=vac.location,
        job_type=vac.job_type,
        status="Applied",
        application_date=datetime.date.today().isoformat(),
        notes=f"Applied via Job Tracker vacancy board."
    )
    db.session.add(app)
    db.session.commit()

    notify_all_hr_users(
        "new_application_received",
        f"New application received for {vac.title} at {vac.company}.",
        related_application=app.id,
        related_vacancy=vac.id,
    )

    return jsonify({"success": True, "message": "Application submitted successfully!"})