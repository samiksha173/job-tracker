from flask import Blueprint, request, session, jsonify, redirect, url_for, render_template
from models import Event
from extensions import db
from datetime import date

events_bp = Blueprint("events", __name__)

def login_required():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return None

@events_bp.route("/calendar")
def calendar_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("calendar.html")

@events_bp.route("/api/events", methods=["GET"])
def list_events():
    err = login_required()
    if err: return err
    uid = session["user_id"]
    month = request.args.get("month")  # YYYY-MM
    query = Event.query.filter_by(user_id=uid)
    if month:
        try:
            y, m = month.split("-")
            query = query.filter(
                db.extract("year", Event.event_date) == int(y),
                db.extract("month", Event.event_date) == int(m)
            )
        except Exception:
            pass
    events = query.order_by(Event.event_date).all()
    return jsonify([e.to_dict() for e in events])

@events_bp.route("/api/events", methods=["POST"])
def create_event():
    err = login_required()
    if err: return err
    data = request.get_json() or {}
    try:
        ed = date.fromisoformat(data["event_date"])
    except Exception:
        return jsonify({"error": "Invalid date"}), 400
    ev = Event(
        user_id=session["user_id"],
        title=data.get("title", ""),
        event_date=ed,
        event_time=data.get("event_time", ""),
        event_type=data.get("event_type", "reminder"),
        note=data.get("note", ""),
    )
    db.session.add(ev)
    db.session.commit()
    return jsonify(ev.to_dict()), 201

@events_bp.route("/api/events/<int:eid>", methods=["DELETE"])
def delete_event(eid):
    err = login_required()
    if err: return err
    ev = Event.query.filter_by(id=eid, user_id=session["user_id"]).first_or_404()
    db.session.delete(ev)
    db.session.commit()
    return jsonify({"success": True})