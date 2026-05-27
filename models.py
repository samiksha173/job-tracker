from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(150), unique=True, nullable=False)
    password      = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), default="applicant")  # "applicant" | "hr"
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    applications  = db.relationship("Application", foreign_keys="Application.user_id",
                                    backref="user", lazy=True, cascade="all, delete-orphan")
    reminders     = db.relationship("Reminder",    backref="user", lazy=True, cascade="all, delete-orphan")
    events        = db.relationship("Event",       backref="user", lazy=True, cascade="all, delete-orphan")


class Application(db.Model):
    __tablename__ = "applications"
    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Basic info
    company          = db.Column(db.String(200), nullable=False)
    position         = db.Column(db.String(200), nullable=False)
    status           = db.Column(db.String(50),  nullable=False, default="Applied")
    job_type         = db.Column(db.String(50))
    location         = db.Column(db.String(200))
    salary           = db.Column(db.String(100))

    # Dates
    application_date = db.Column(db.Date)
    deadline         = db.Column(db.Date)
    interview_date   = db.Column(db.Date)

    # Resume
    resume_filename  = db.Column(db.String(300))

    # Details
    job_description  = db.Column(db.Text)
    notes            = db.Column(db.Text)
    contact_person   = db.Column(db.String(150))
    contact_email    = db.Column(db.String(150))
    job_url          = db.Column(db.String(500))

    # HR fields
    hr_status        = db.Column(db.String(50), default="Pending")   # Pending / Eligible / Not Eligible / Interview / Hired / Rejected
    hr_notes         = db.Column(db.Text)
    hr_reviewed_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    hr_reviewed_at   = db.Column(db.DateTime, nullable=True)

    # Soft delete
    deleted          = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reviewer         = db.relationship("User", foreign_keys=[hr_reviewed_by])

    def to_dict(self, include_applicant=False):
        d = {
            "id":               self.id,
            "company":          self.company,
            "position":         self.position,
            "status":           self.status,
            "job_type":         self.job_type or "",
            "location":         self.location or "",
            "salary":           self.salary or "",
            "application_date": str(self.application_date)  if self.application_date  else "",
            "deadline":         str(self.deadline)           if self.deadline           else "",
            "interview_date":   str(self.interview_date)    if self.interview_date    else "",
            "resume_filename":  self.resume_filename or "",
            "job_description":  self.job_description or "",
            "notes":            self.notes or "",
            "contact_person":   self.contact_person or "",
            "contact_email":    self.contact_email or "",
            "job_url":          self.job_url or "",
            "hr_status":        self.hr_status or "Pending",
            "hr_notes":         self.hr_notes or "",
            "hr_reviewed_at":   str(self.hr_reviewed_at) if self.hr_reviewed_at else "",
            "deleted":          self.deleted,
            "created_at":       str(self.created_at),
        }
        if include_applicant and self.user:
            d["applicant_name"]  = self.user.name
            d["applicant_email"] = self.user.email
        return d


class Reminder(db.Model):
    __tablename__ = "reminders"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title         = db.Column(db.String(300), nullable=False)
    remind_date   = db.Column(db.Date, nullable=False)
    remind_time   = db.Column(db.String(10))
    note          = db.Column(db.Text)
    reminder_type = db.Column(db.String(50), default="reminder")
    done          = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":            self.id,
            "title":         self.title,
            "remind_date":   str(self.remind_date),
            "remind_time":   self.remind_time or "",
            "note":          self.note or "",
            "reminder_type": self.reminder_type,
            "done":          self.done,
        }


class Event(db.Model):
    __tablename__ = "events"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title       = db.Column(db.String(300), nullable=False)
    event_date  = db.Column(db.Date, nullable=False)
    event_time  = db.Column(db.String(10))
    event_type  = db.Column(db.String(50), default="reminder")
    note        = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id":         self.id,
            "title":      self.title,
            "event_date": str(self.event_date),
            "event_time": self.event_time or "",
            "event_type": self.event_type,
            "note":       self.note or "",
        }