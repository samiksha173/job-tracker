from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
from models import Application, User
from extensions import db
from datetime import datetime

hr_bp = Blueprint("hr", __name__, url_prefix="/hr")

# ── Guard ─────────────────────────────────────────────────────────────────────
def hr_required():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "hr":
        return redirect(url_for("auth.index"))
    return None

def hr_api_guard():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    if session.get("role") != "hr":
        return jsonify({"error": "HR access required"}), 403
    return None

# ── Pages ─────────────────────────────────────────────────────────────────────

@hr_bp.route("/")
@hr_bp.route("/dashboard")
def hr_dashboard():
    g = hr_required()
    if g: return g
    return render_template("hr/dashboard.html", active="hr_dashboard")

@hr_bp.route("/applications")
def hr_applications():
    g = hr_required()
    if g: return g
    return render_template("hr/applications.html", active="hr_applications")

@hr_bp.route("/applicants")
def hr_applicants():
    g = hr_required()
    if g: return g
    return render_template("hr/applicants.html", active="hr_applicants")

# ── API: Stats ────────────────────────────────────────────────────────────────

@hr_bp.route("/api/stats")
def hr_stats():
    g = hr_api_guard()
    if g: return g
    apps = Application.query.filter_by(deleted=False).all()
    total_applicants = User.query.filter_by(role="applicant").count()
    return jsonify({
        "total":            len(apps),
        "pending":          sum(1 for a in apps if a.hr_status == "Pending"),
        "eligible":         sum(1 for a in apps if a.hr_status == "Eligible"),
        "not_eligible":     sum(1 for a in apps if a.hr_status == "Not Eligible"),
        "interview":        sum(1 for a in apps if a.hr_status == "Interview"),
        "hired":            sum(1 for a in apps if a.hr_status == "Hired"),
        "rejected":         sum(1 for a in apps if a.hr_status == "Rejected"),
        "total_applicants": total_applicants,
    })

# ── API: All applications (HR view) ──────────────────────────────────────────

@hr_bp.route("/api/applications")
def hr_list_applications():
    g = hr_api_guard()
    if g: return g

    hr_status = request.args.get("hr_status", "")
    position  = request.args.get("position", "")
    search    = request.args.get("search", "").lower()

    query = Application.query.filter_by(deleted=False)
    if hr_status:
        query = query.filter_by(hr_status=hr_status)
    if position:
        query = query.filter(Application.position.ilike(f"%{position}%"))

    apps = query.order_by(Application.created_at.desc()).all()

    result = []
    for a in apps:
        d = a.to_dict(include_applicant=True)
        if search and \
           search not in d.get("applicant_name",  "").lower() and \
           search not in d.get("company",          "").lower() and \
           search not in d.get("position",         "").lower():
            continue
        result.append(d)
    return jsonify(result)

# ── API: Single application detail ───────────────────────────────────────────

@hr_bp.route("/api/applications/<int:app_id>")
def hr_get_application(app_id):
    g = hr_api_guard()
    if g: return g
    a = Application.query.filter_by(id=app_id, deleted=False).first_or_404()
    return jsonify(a.to_dict(include_applicant=True))

# ── API: Update HR status ─────────────────────────────────────────────────────

@hr_bp.route("/api/applications/<int:app_id>/review", methods=["POST"])
def hr_review(app_id):
    g = hr_api_guard()
    if g: return g
    a = Application.query.filter_by(id=app_id, deleted=False).first_or_404()
    data = request.get_json() or {}

    hr_status = data.get("hr_status")
    hr_notes  = data.get("hr_notes", "")

    valid = ["Pending", "Eligible", "Not Eligible", "Interview", "Hired", "Rejected"]
    if hr_status not in valid:
        return jsonify({"error": f"Invalid status. Choose from {valid}"}), 400

    a.hr_status      = hr_status
    a.hr_notes       = hr_notes
    a.hr_reviewed_by = session["user_id"]
    a.hr_reviewed_at = datetime.utcnow()

    # Sync back to applicant-visible status
    status_map = {
        "Eligible":     "Applied",
        "Not Eligible": "Rejected",
        "Interview":    "Interview",
        "Hired":        "Offer",
        "Rejected":     "Rejected",
        "Pending":      "Applied",
    }
    a.status = status_map.get(hr_status, a.status)
    db.session.commit()
    return jsonify({"success": True, "application": a.to_dict(include_applicant=True)})

# ── API: All unique positions (for filter dropdown) ───────────────────────────

@hr_bp.route("/api/positions")
def hr_positions():
    g = hr_api_guard()
    if g: return g
    rows = db.session.query(Application.position).filter_by(deleted=False).distinct().all()
    return jsonify([r[0] for r in rows if r[0]])

# ── API: All applicants ───────────────────────────────────────────────────────

@hr_bp.route("/api/applicants")
def hr_applicants_api():
    g = hr_api_guard()
    if g: return g
    users = User.query.filter_by(role="applicant").all()
    result = []
    for u in users:
        apps = Application.query.filter_by(user_id=u.id, deleted=False).all()
        result.append({
            "id":         u.id,
            "name":       u.name,
            "email":      u.email,
            "total_apps": len(apps),
            "statuses":   list(set(a.hr_status for a in apps)),
            "joined":     str(u.created_at.date()),
        })
    return jsonify(result)