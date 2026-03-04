import os
from datetime import date, datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE_PATH = os.path.join(INSTANCE_DIR, "placement_portal.db")


app = Flask(__name__, instance_path=INSTANCE_DIR, instance_relative_config=True)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEFAULT_ADMIN_USERNAME"] = "admin"
app.config["DEFAULT_ADMIN_PASSWORD"] = "admin123"
app.config["DEFAULT_ADMIN_EMAIL"] = "admin@placement.local"

os.makedirs(INSTANCE_DIR, exist_ok=True)

db = SQLAlchemy(app)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Admin(TimestampMixin, db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Company(TimestampMixin, db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    hr_contact_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    approval_status = db.Column(db.String(20), default="pending", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)

    drives = db.relationship(
        "PlacementDrive",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    placements = db.relationship("PlacementRecord", back_populates="company", lazy="dynamic")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class Student(TimestampMixin, db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    degree = db.Column(db.String(120), nullable=True)
    branch = db.Column(db.String(120), nullable=True)
    cgpa = db.Column(db.Float, nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    skills = db.Column(db.Text, nullable=True)
    resume_filename = db.Column(db.String(255), nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)

    applications = db.relationship(
        "Application",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    placements = db.relationship("PlacementRecord", back_populates="student", lazy="dynamic")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)


class PlacementDrive(TimestampMixin, db.Model):
    __tablename__ = "placement_drives"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.Text, nullable=True)
    salary_lpa = db.Column(db.Float, nullable=True)
    location = db.Column(db.String(120), nullable=True)

    application_deadline = db.Column(db.Date, nullable=False)
    drive_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="pending", nullable=False)

    company = db.relationship("Company", back_populates="drives")
    applications = db.relationship(
        "Application",
        back_populates="drive",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def is_open(self) -> bool:
        return self.status == "approved" and self.application_deadline >= date.today()


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("student_id", "drive_id", name="uq_student_drive_application"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id"), nullable=False)

    application_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default="applied", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    student = db.relationship("Student", back_populates="applications")
    drive = db.relationship("PlacementDrive", back_populates="applications")
    placement = db.relationship(
        "PlacementRecord",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )


class PlacementRecord(TimestampMixin, db.Model):
    __tablename__ = "placement_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.id"), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), unique=True, nullable=False)

    designation = db.Column(db.String(150), nullable=False)
    package_lpa = db.Column(db.Float, nullable=True)
    placement_date = db.Column(db.Date, default=date.today, nullable=False)

    student = db.relationship("Student", back_populates="placements")
    company = db.relationship("Company", back_populates="placements")
    drive = db.relationship("PlacementDrive")
    application = db.relationship("Application", back_populates="placement")


def initialize_database() -> None:
    db.create_all()
    seed_default_admin()


def seed_default_admin() -> None:
    username = app.config["DEFAULT_ADMIN_USERNAME"]
    password = app.config["DEFAULT_ADMIN_PASSWORD"]
    email = app.config["DEFAULT_ADMIN_EMAIL"]

    admin = Admin.query.filter_by(username=username).first()
    if admin:
        return

    admin = Admin(
        username=username,
        email=email,
        full_name="Placement Cell Admin",
        is_active=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()


@app.route("/")
def index():
    return "Placement Portal database models and schema are ready."


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
