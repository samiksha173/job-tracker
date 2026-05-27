from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Mail, Message
from models import User
from extensions import db

auth_bp = Blueprint("auth", __name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

def send_reset_email(user_email, reset_url):
    mail = Mail(current_app)
    msg = Message(
        subject="Job Tracker – Password Reset Request",
        sender=current_app.config["MAIL_DEFAULT_SENDER"],
        recipients=[user_email]
    )
    msg.body = f"""Hello,

You requested a password reset for your Job Tracker account.

Click the link below to reset your password (valid for 30 minutes):

{reset_url}

If you did not request this, please ignore this email. Your password will not change.

— Job Tracker Team
"""
    msg.html = f"""
<div style="font-family:'Segoe UI',sans-serif;max-width:480px;margin:auto;padding:32px;
     background:#f0faf4;border-radius:16px;">
  <div style="text-align:center;margin-bottom:24px;">
    <span style="font-size:2rem;">💼</span>
    <h2 style="color:#111;margin:8px 0 0;">Job Tracker</h2>
  </div>
  <div style="background:#fff;border-radius:12px;padding:28px;">
    <h3 style="color:#111;margin-top:0;">Password Reset Request</h3>
    <p style="color:#6b7280;line-height:1.6;">
      You requested a password reset for your Job Tracker account.<br>
      Click the button below to reset your password.<br>
      <strong>This link is valid for 30 minutes.</strong>
    </p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{reset_url}"
         style="background:linear-gradient(135deg,#10b981,#059669);color:#fff;
                padding:13px 32px;border-radius:30px;text-decoration:none;
                font-weight:700;font-size:1rem;display:inline-block;">
        Reset My Password →
      </a>
    </div>
    <p style="color:#9ca3af;font-size:.82rem;">
      If you did not request this, simply ignore this email.
      Your password will not change.
    </p>
  </div>
</div>
"""
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
        session["user_id"]   = user.id
        session["user_name"] = user.name
        session["role"]      = user.role
        dest = url_for("hr.hr_dashboard") if user.role == "hr" else url_for("auth.index")
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
    return jsonify({"id": session["user_id"], "name": session["user_name"], "role": session.get("role", "applicant")})

# ── Forgot Password ───────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json() or request.form
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required."}), 400

    # Always return success to avoid revealing whether email exists
    user = User.query.filter_by(email=email).first()
    if user:
        try:
            s         = get_serializer()
            token     = s.dumps(email, salt="password-reset-salt")
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            send_reset_email(email, reset_url)
        except Exception as e:
            current_app.logger.error(f"Failed to send reset email to {email}: {e}")
            return jsonify({"success": False, "message": "Failed to send email. Please try again later."}), 500

    return jsonify({
        "success": True,
        "message": f"If an account exists for {email}, a reset link has been sent to your inbox."
    })

# ── Reset Password (GET = show form, POST = save new password) ────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    s = get_serializer()
    try:
        # Token expires after 30 minutes (1800 seconds)
        email = s.loads(token, salt="password-reset-salt", max_age=1800)
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

    # GET — show the reset form
    return render_template("reset_password.html", token=token, error=None)