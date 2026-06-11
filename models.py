from extensions import db
import datetime


class User(db.Model):
    __tablename__ = "user"
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(120), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role     = db.Column(db.String(20), default="applicant")   # "applicant" | "hr"
    company  = db.Column(db.String(120))                        # filled for HR users


class Application(db.Model):
    __tablename__ = "application"
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    company          = db.Column(db.String(120), nullable=False)
    position         = db.Column(db.String(120), nullable=False)
    status           = db.Column(db.String(50), default="Applied")
    application_date = db.Column(db.String(20))
    deadline         = db.Column(db.String(20))
    location         = db.Column(db.String(120))
    job_type         = db.Column(db.String(50))
    salary           = db.Column(db.String(80))
    job_description  = db.Column(db.Text)
    notes            = db.Column(db.Text)
    resume_filename  = db.Column(db.String(256))
    deleted          = db.Column(db.Boolean, default=False)
    # HR fields
    hr_status           = db.Column(db.String(50), default="Pending")
    hr_notes            = db.Column(db.Text)
    interview_datetime  = db.Column(db.String(30))


class Reminder(db.Model):
    __tablename__ = "reminder"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title         = db.Column(db.String(200), nullable=False)
    reminder_type = db.Column(db.String(50), default="Other")
    remind_date   = db.Column(db.String(20))
    note          = db.Column(db.Text)
    completed     = db.Column(db.Boolean, default=False)


class Event(db.Model):
    __tablename__ = "event"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.String(20))
    event_time = db.Column(db.String(10))
    event_type = db.Column(db.String(50), default="reminder")
    note       = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title or "",
            "event_date": self.event_date or "",
            "event_time": self.event_time or "",
            "event_type": self.event_type or "reminder",
            "note": self.note or "",
        }


class UserProfile(db.Model):
    __tablename__ = "user_profile"
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    profile_data     = db.Column(db.Text, nullable=False, default="{}")
    job_title        = db.Column(db.String(120))
    company_website  = db.Column(db.String(255))
    phone_number     = db.Column(db.String(40))
    work_email       = db.Column(db.String(120))
    linkedin_url     = db.Column(db.String(255))
    location         = db.Column(db.String(200))
    bio              = db.Column(db.Text)
    avatar_filename  = db.Column(db.String(255))
    email_notifications = db.Column(db.Boolean, default=True)
    created_at       = db.Column(db.String(30), default=lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at       = db.Column(db.String(30), default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self):
        try:
            import json
            payload = json.loads(self.profile_data or "{}")
        except Exception:
            payload = {}

        payload.update({
            "job_title": self.job_title,
            "company_website": self.company_website,
            "phone_number": self.phone_number,
            "work_email": self.work_email,
            "linkedin_url": self.linkedin_url,
            "location": self.location,
            "bio": self.bio,
            "avatar_filename": self.avatar_filename,
            "email_notifications": self.email_notifications,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        })
        return payload


class InterviewSession(db.Model):
    __tablename__ = "interview_session"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role = db.Column(db.String(120), nullable=False, default="SDE")
    difficulty = db.Column(db.String(50), default="Medium")
    interview_type = db.Column(db.String(80), default="Mixed")
    language = db.Column(db.String(50), default="English")
    question_count = db.Column(db.Integer, default=0)
    overall_score = db.Column(db.Float, default=0.0)
    questions_json = db.Column(db.Text)
    report_json = db.Column(db.Text)
    created_at = db.Column(db.String(30), default=lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "difficulty": self.difficulty,
            "interview_type": self.interview_type,
            "language": self.language,
            "question_count": self.question_count,
            "overall_score": self.overall_score,
            "questions": json.loads(self.questions_json or "[]"),
            "report": json.loads(self.report_json or "{}"),
            "created_at": self.created_at,
        }


class Message(db.Model):
    __tablename__ = "message"
    id             = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=False)
    sender         = db.Column(db.String(20))   # "hr" | "applicant"
    message        = db.Column(db.Text, nullable=False)
    sent_at        = db.Column(db.String(30), default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))


# ── NEW: Job Vacancy posted by HR ─────────────────────────────────────────────
class JobVacancy(db.Model):
    __tablename__ = "job_vacancy"
    id           = db.Column(db.Integer, primary_key=True)
    posted_by    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title        = db.Column(db.String(200), nullable=False)
    company      = db.Column(db.String(120), nullable=False)
    location     = db.Column(db.String(120))
    job_type     = db.Column(db.String(50), default="Full-time")
    experience   = db.Column(db.String(80))
    salary       = db.Column(db.String(80))
    description  = db.Column(db.Text)
    requirements = db.Column(db.Text)
    skills       = db.Column(db.String(300))
    deadline     = db.Column(db.String(20))
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.String(30), default=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))

    def to_dict(self):
        return {
            "id":           self.id,
            "posted_by":    self.posted_by,
            "title":        self.title,
            "company":      self.company,
            "location":     self.location or "",
            "job_type":     self.job_type or "Full-time",
            "experience":   self.experience or "",
            "salary":       self.salary or "",
            "description":  self.description or "",
            "requirements": self.requirements or "",
            "skills":       self.skills or "",
            "deadline":     self.deadline or "",
            "is_active":    self.is_active,
            "created_at":   self.created_at,
        }


class Notification(db.Model):
    __tablename__ = "notification"
    id                  = db.Column(db.Integer, primary_key=True)
    hr_user             = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    type                = db.Column(db.String(80), nullable=False)
    message             = db.Column(db.Text, nullable=False)
    is_read             = db.Column(db.Boolean, default=False)
    created_at          = db.Column(db.String(30), default=lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    related_application = db.Column(db.Integer, db.ForeignKey("application.id"), nullable=True)
    related_vacancy     = db.Column(db.Integer, db.ForeignKey("job_vacancy.id"), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "hr_user": self.hr_user,
            "type": self.type,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at,
            "relative_time": format_relative_time(self.created_at),
            "related_application": self.related_application,
            "related_vacancy": self.related_vacancy,
        }


def format_relative_time(created_at):
    try:
        dt = datetime.datetime.strptime(str(created_at), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt = datetime.datetime.fromisoformat(str(created_at))
        except ValueError:
            return "just now"

    diff = datetime.datetime.utcnow() - dt
    total_seconds = max(int(diff.total_seconds()), 0)
    if total_seconds < 60:
        return "just now"
    if total_seconds < 3600:
        mins = max(1, total_seconds // 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    if total_seconds < 86400:
        hours = max(1, total_seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = max(1, total_seconds // 86400)
    return f"{days} day{'s' if days != 1 else ''} ago"


def get_notification_key(hr_user, type, related_application=None, related_vacancy=None):
    return (hr_user, type, related_application, related_vacancy)


def notification_exists(hr_user, type, related_application=None, related_vacancy=None):
    query = Notification.query.filter_by(hr_user=hr_user, type=type)
    if related_application is not None:
        query = query.filter_by(related_application=related_application)
    if related_vacancy is not None:
        query = query.filter_by(related_vacancy=related_vacancy)
    return query.first()


def create_notification(hr_user, type, message, related_application=None, related_vacancy=None):
    if hr_user is None:
        return None
    existing = notification_exists(hr_user, type, related_application, related_vacancy)
    if existing:
        return existing
    n = Notification(
        hr_user=hr_user,
        type=type,
        message=message,
        is_read=False,
        related_application=related_application,
        related_vacancy=related_vacancy,
    )
    db.session.add(n)
    db.session.commit()
    return n


def notify_all_hr_users(type, message, related_application=None, related_vacancy=None):
    created = []
    for user in User.query.filter_by(role="hr").all():
        notif = create_notification(
            user.id,
            type,
            message,
            related_application=related_application,
            related_vacancy=related_vacancy,
        )
        if notif:
            created.append(notif)
    return created


def sync_vacancy_deadline_notifications():
    from datetime import datetime, timedelta

    today = datetime.utcnow().date()
    next_day = today + timedelta(days=1)
    created = []

    for vac in JobVacancy.query.filter(JobVacancy.deadline.isnot(None), JobVacancy.is_active.is_(True)).all():
        try:
            deadline = datetime.strptime(vac.deadline, "%Y-%m-%d").date()
        except ValueError:
            continue

        if deadline < today:
            notif_type = "vacancy_expired"
            notif_msg = f"Vacancy \"{vac.title}\" expired on {vac.deadline}."
        elif deadline <= next_day:
            notif_type = "vacancy_deadline_approaching"
            notif_msg = f"Vacancy \"{vac.title}\" deadline is approaching ({vac.deadline})."
        else:
            continue

        existing = notification_exists(vac.posted_by, notif_type, related_vacancy=vac.id)
        if existing:
            continue

        notif = create_notification(
            vac.posted_by,
            notif_type,
            notif_msg,
            related_vacancy=vac.id,
        )
        if notif:
            created.append(notif)

    return created
