from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
from models import Reminder
from extensions import db
from datetime import date

reminders_bp = Blueprint("reminders", __name__)

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

def reminder_to_dict(r):
    return {
        "id": r.id,
        "user_id": r.user_id,
        "title": r.title or "",
        "reminder_type": r.reminder_type or "other",
        "remind_date": r.remind_date or "",
        "remind_time": "",
        "note": r.note or "",
        "completed": bool(r.completed),
    }

@reminders_bp.route("/reminders")
def reminders_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("reminders.html")

@reminders_bp.route("/api/reminders", methods=["GET"])
def list_reminders():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    today = date.today().isoformat()
    items = Reminder.query.filter_by(user_id=uid, completed=False)\
        .filter(Reminder.remind_date >= today)\
        .order_by(Reminder.remind_date).all()
    return jsonify([reminder_to_dict(r) for r in items])

@reminders_bp.route("/api/reminders", methods=["POST"])
def create_reminder():
    err = login_required()
    if err: return err
    data = request.get_json() or {}
    try:
        rd = date.fromisoformat(data["remind_date"])
    except Exception:
        return jsonify({"error": "Invalid date"}), 400
    r = Reminder(
        user_id=session["user_id"],
        title=data.get("title", ""),
        remind_date=rd.isoformat(),
        note=data.get("note", ""),
        reminder_type=data.get("reminder_type", "reminder"),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(reminder_to_dict(r)), 201

@reminders_bp.route("/api/reminders/<int:rid>", methods=["DELETE"])
def delete_reminder(rid):
    err = login_required()
    if err: return err
    r = Reminder.query.filter_by(id=rid, user_id=session["user_id"]).first_or_404()
    db.session.delete(r)
    db.session.commit()
    return jsonify({"success": True})

@reminders_bp.route("/api/reminders/<int:rid>/done", methods=["POST"])
def mark_done(rid):
    err = login_required()
    if err: return err
    r = Reminder.query.filter_by(id=rid, user_id=session["user_id"]).first_or_404()
    r.completed = True
    db.session.commit()
    return jsonify({"success": True})
