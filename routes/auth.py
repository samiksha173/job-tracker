import json
import datetime

from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from models import User, UserProfile
from extensions import db

auth_bp = Blueprint("auth", __name__)

def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

def send_reset_email(user_email, reset_url):
    mail = Mail(current_app._get_current_object())
    msg  = Message(
        subject   = "Job Tracker – Password Reset Request",
        recipients= [user_email]
    )
    msg.body = (
        f"Hello,\n\n"
        f"You requested a password reset for your Job Tracker account.\n\n"
        f"Click the link below to reset your password (valid for 30 minutes):\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, ignore this email.\n\n"
        f"— Job Tracker Team"
    )
    msg.html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f0faf4;font-family:'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
  <tr><td align="center">
    <table width="480" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border-radius:18px;
                  box-shadow:0 8px 30px rgba(0,0,0,0.10);overflow:hidden;">

      <tr>
        <td style="background:linear-gradient(135deg,#10b981,#059669);
                    padding:32px 40px;text-align:center;">
          <p style="margin:0;font-size:2rem;">💼</p>
          <h1 style="margin:8px 0 0;color:#fff;font-size:1.4rem;font-weight:800;">
            Job Tracker
          </h1>
        </td>
      </tr>

      <tr>
        <td style="padding:36px 40px;">
          <h2 style="margin:0 0 12px;color:#111;font-size:1.2rem;font-weight:800;">
            Password Reset Request
          </h2>
          <p style="margin:0 0 10px;color:#6b7280;line-height:1.7;font-size:.93rem;">
            We received a request to reset the password for your Job Tracker account
            linked to <strong>{user_email}</strong>.
          </p>
          <p style="margin:0 0 28px;color:#6b7280;line-height:1.7;font-size:.93rem;">
            Click the button below to set a new password.
            <strong>This link expires in 30 minutes.</strong>
          </p>
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td align="center">
                <a href="{reset_url}"
                   style="display:inline-block;
                          background:linear-gradient(135deg,#10b981,#059669);
                          color:#fff;text-decoration:none;
                          padding:14px 36px;border-radius:30px;
                          font-size:1rem;font-weight:700;">
                  Reset My Password &rarr;
                </a>
              </td>
            </tr>
          </table>
          <p style="margin:24px 0 0;font-size:.78rem;color:#9ca3af;line-height:1.6;">
            If the button doesn't work, copy and paste this link into your browser:<br/>
            <a href="{reset_url}" style="color:#10b981;word-break:break-all;">{reset_url}</a>
          </p>
        </td>
      </tr>

      <tr>
        <td style="background:#f9fafb;padding:20px 40px;
                    border-top:1px solid #e5e7eb;text-align:center;">
          <p style="margin:0;font-size:.78rem;color:#9ca3af;line-height:1.6;">
            If you did not request this, you can safely ignore this email.<br/>
            Your password will <strong>not</strong> change.
          </p>
          <p style="margin:10px 0 0;font-size:.75rem;color:#d1d5db;">
            &copy; 2025 Job Tracker. All rights reserved.
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""
    mail.send(msg)


# ── Pages ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    if session.get("role") == "hr":
        return redirect(url_for("hr.hr_dashboard"))
    return render_template("index.html", active="dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data     = request.get_json() or request.form
        email    = data.get("email", "").strip()
        password = data.get("password", "")
        role     = data.get("role", "applicant")

        user = User.query.filter_by(email=email, role=role).first()
        if user and check_password_hash(user.password, password):
            session["user_id"]   = user.id
            session["user_name"] = user.name
            session["role"]      = user.role
            dest = url_for("hr.hr_dashboard") if user.role == "hr" else url_for("auth.index")
            return jsonify({"success": True, "redirect": dest, "role": user.role})
        return jsonify({"success": False, "message": "Invalid credentials or wrong role selected"}), 401
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data     = request.get_json() or request.form
        name     = data.get("name", "").strip()
        email    = data.get("email", "").strip()
        password = data.get("password", "")
        role     = data.get("role", "applicant")

        if not name or not email or not password:
            return jsonify({"success": False, "message": "All fields are required"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "Email already registered"}), 409

        user = User(name=name, email=email,
                    password=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.commit()
        page = "page-hr-login" if role == "hr" else "page-applicant-login"
        dest = url_for("auth.login") + f"?page={page}"
        return jsonify({"success": True, "redirect": dest, "role": user.role})
    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(session["user_id"])
    profile = UserProfile.query.filter_by(user_id=session["user_id"]).first()
    avatar_url = None
    if profile and profile.avatar_filename:
        avatar_url = f"/media/hr_avatars/{profile.avatar_filename}"

    return jsonify({
        "id": session["user_id"],
        "name": session["user_name"],
        "role": session.get("role", "applicant"),
        "company": user.company if user else None,
        "avatar_url": avatar_url,
        "job_title": profile.job_title if profile else None,
    })


@auth_bp.route("/api/profile", methods=["GET", "POST"])
def profile_api():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    user_id = session["user_id"]
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if request.method == "GET":
        saved_profile = UserProfile.query.filter_by(user_id=user_id).first()
        if saved_profile:
            profile_dict = saved_profile.to_dict()
            if saved_profile.avatar_filename and not profile_dict.get('photo'):
                profile_dict['photo'] = url_for('serve_hr_avatar', filename=saved_profile.avatar_filename)
            return jsonify(profile_dict)
        return jsonify({})

    data = request.get_json(silent=True) or {}
    payload = {
        "name": str(data.get("name") or "").strip(),
        "role": str(data.get("role") or "").strip(),
        "email": str(data.get("email") or "").strip(),
        "phone": str(data.get("phone") or "").strip(),
        "location": str(data.get("location") or "").strip(),
        "bio": str(data.get("bio") or "").strip(),
        "skills": str(data.get("skills") or "").strip(),
        "linkedin": str(data.get("linkedin") or "").strip(),
        "portfolio": str(data.get("portfolio") or "").strip(),
        "photo": str(data.get("photo") or "").strip(),
    }

    if payload["name"]:
        user.name = payload["name"]
        session["user_name"] = payload["name"]

    existing = UserProfile.query.filter_by(user_id=user_id).first()
    if existing:
        existing.profile_data = json.dumps(payload)
        existing.updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        existing = UserProfile(user_id=user_id, profile_data=json.dumps(payload))
        db.session.add(existing)

    db.session.commit()
    return jsonify(payload)


# ── Forgot Password ───────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json() or request.form
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        try:
            s         = get_serializer()
            token     = s.dumps(email, salt="password-reset-salt")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_reset_email(email, reset_url)
        except Exception as e:
            current_app.logger.error(f"Reset email failed for {email}: {e}")
            return jsonify({
                "success": False,
                "message": f"Failed to send email. Error: {str(e)}"
            }), 500

    # Always return success whether email exists or not (security best practice)
    return jsonify({
        "success": True,
        "message": f"If an account exists for {email}, a reset link has been sent to your inbox."
    })


# ── Reset Password ────────────────────────────────────────────────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = get_serializer()
    try:
        email = s.loads(token, salt="password-reset-salt", max_age=1800)  # 30 min
    except SignatureExpired:
        return render_template("reset_password.html",
                               error="This reset link has expired. Please request a new one.",
                               token=None)
    except BadSignature:
        return render_template("reset_password.html",
                               error="This reset link is invalid.",
                               token=None)

    if request.method == "POST":
        data         = request.get_json() or request.form
        new_password = data.get("password", "")
        confirm      = data.get("confirm", "")

        if len(new_password) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters."}), 400
        if new_password != confirm:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"success": False, "message": "Account not found."}), 404

        user.password = generate_password_hash(new_password)
        db.session.commit()
        return jsonify({"success": True, "message": "Password updated successfully! You can now sign in."})

    return render_template("reset_password.html", token=token, error=None)