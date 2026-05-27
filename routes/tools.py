from flask import Blueprint, session, jsonify, redirect, url_for, render_template
from models import Application
from extensions import db
import os

tools_bp = Blueprint("tools", __name__)

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

@tools_bp.route("/tools")
def tools_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("tools.html")

@tools_bp.route("/api/tools/recycle-bin", methods=["GET"])
def recycle_bin():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    apps = Application.query.filter_by(user_id=uid, deleted=True).all()
    return jsonify([a.to_dict() for a in apps])

@tools_bp.route("/api/tools/recycle-bin/empty", methods=["DELETE"])
def empty_bin():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    Application.query.filter_by(user_id=uid, deleted=True).delete()
    db.session.commit()
    return jsonify({"success": True})

@tools_bp.route("/api/tools/storage-info", methods=["GET"])
def storage_info():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    total = Application.query.filter_by(user_id=uid, deleted=False).count()
    deleted = Application.query.filter_by(user_id=uid, deleted=True).count()
    return jsonify({"total_applications": total, "recycle_bin": deleted})

@tools_bp.route("/api/tools/load-demo", methods=["POST"])
def load_demo():
    err = login_required()
    if err: return err
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
        app = Application(user_id=uid, **d)
        db.session.add(app)
    db.session.commit()
    return jsonify({"success": True, "loaded": len(demos)})