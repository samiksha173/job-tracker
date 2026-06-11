from flask import Blueprint, session, jsonify, redirect, url_for, render_template
from models import Application
from extensions import db
from sqlalchemy import inspect, text
import os

tools_bp = Blueprint("tools", __name__)

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

def ensure_deleted_column():
    inspector = inspect(db.engine)
    cols = [c["name"] for c in inspector.get_columns("application")]
    if "deleted" not in cols:
        db.session.execute(text("ALTER TABLE application ADD COLUMN deleted BOOLEAN DEFAULT 0"))
        db.session.commit()

def application_to_dict(a):
    return {
        "id": a.id,
        "user_id": a.user_id,
        "company": a.company or "",
        "position": a.position or "",
        "status": a.status or "Applied",
        "application_date": a.application_date or "",
        "deadline": a.deadline or "",
        "location": a.location or "",
        "job_type": a.job_type or "",
        "salary": a.salary or "",
        "notes": a.notes or "",
        "deleted": bool(getattr(a, "deleted", False)),
    }

@tools_bp.route("/tools")
def tools_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("tools.html")

@tools_bp.route("/api/tools/recycle-bin", methods=["GET"])
def recycle_bin():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=True).all()
    return jsonify([application_to_dict(a) for a in apps])

@tools_bp.route("/api/tools/recycle-bin/empty", methods=["DELETE"])
def empty_bin():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    Application.query.filter_by(user_id=uid, deleted=True).delete()
    db.session.commit()
    return jsonify({"success": True})

@tools_bp.route("/api/tools/storage-info", methods=["GET"])
def storage_info():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    total = Application.query.filter_by(user_id=uid, deleted=False).count()
    deleted = Application.query.filter_by(user_id=uid, deleted=True).count()
    return jsonify({"total_applications": total, "recycle_bin": deleted})

@tools_bp.route("/api/tools/load-demo", methods=["POST"])
def load_demo():
    err = login_required()
    if err: return err
    ensure_deleted_column()
    uid = session["user_id"]
    from datetime import date, timedelta
    demos = [
        {"company": "Google", "position": "Software Engineer Intern", "status": "Interview",
         "job_type": "Internship", "location": "Bangalore", "salary": "₹80,000/mo",
         "application_date": date.today() - timedelta(days=10),
         "deadline": date.today() + timedelta(days=5),
         "interview_date": date.today() + timedelta(days=2)},
        {"company": "Amazon", "position": "SDE-1", "status": "Applied",
         "job_type": "Full-Time", "location": "Hyderabad", "salary": "₹25 LPA",
         "application_date": date.today() - timedelta(days=5),
         "deadline": date.today() + timedelta(days=10)},
        {"company": "Infosys", "position": "Systems Engineer", "status": "Offer",
         "job_type": "Full-Time", "location": "Pune", "salary": "₹6.5 LPA",
         "application_date": date.today() - timedelta(days=30)},
        {"company": "Startify", "position": "Frontend Developer Intern", "status": "Rejected",
         "job_type": "Internship", "location": "Remote", "salary": "₹20,000/mo",
         "application_date": date.today() - timedelta(days=20)},
    ]
    for d in demos:
        record = dict(d)
        if "interview_date" in record:
            record["interview_datetime"] = record.pop("interview_date")
        app = Application(user_id=uid, **record)
        db.session.add(app)
    db.session.commit()
    return jsonify({"success": True, "loaded": len(demos)})
