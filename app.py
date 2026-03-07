import os
from datetime import date, datetime
from functools import wraps
from uuid import uuid4

from flask import (
    Blueprint,
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect, or_
from werkzeug.datastructures import FileStorage
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads", "resumes")
DATABASE_PATH = os.path.join(INSTANCE_DIR, "placement_portal.db")


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    instance_path=INSTANCE_DIR,
    instance_relative_config=True,
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DATABASE_PATH}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["ALLOWED_RESUME_EXTENSIONS"] = {"pdf", "doc", "docx"}
app.config["DEFAULT_ADMIN_USERNAME"] = "admin"
app.config["DEFAULT_ADMIN_PASSWORD"] = "admin123"
app.config["DEFAULT_ADMIN_EMAIL"] = "admin@placement.local"
app.config["SESSION_BOOT_TOKEN"] = datetime.utcnow().isoformat()

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


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
    experience_required = db.Column(db.String(120), nullable=True)
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
    ensure_schema_updates()
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


def ensure_schema_updates() -> None:
    inspector = inspect(db.engine)
    if "placement_drives" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("placement_drives")}
    if "experience_required" not in existing_columns:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE placement_drives ADD COLUMN experience_required VARCHAR(120)"
            )


def login_actor(role: str, user_id: int) -> None:
    session.clear()
    session["_boot_token"] = app.config["SESSION_BOOT_TOKEN"]
    session["user_role"] = role
    session["user_id"] = user_id


def logout_actor() -> None:
    session.clear()


def get_current_role():
    return session.get("user_role")


def get_current_user():
    role = get_current_role()
    user_id = session.get("user_id")
    if role is None or user_id is None:
        return None

    model_map = {
        "admin": Admin,
        "company": Company,
        "student": Student,
    }
    model = model_map.get(role)
    if model is None:
        return None

    return db.session.get(model, user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if get_current_user() is None:
            flash("Please login to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            role = get_current_role()
            if role not in allowed_roles:
                flash("You are not authorized to access this page.", "danger")
                return redirect(url_for("main.index"))
            return view_func(*args, **kwargs)

        return wrapped_view

    return decorator


def account_access_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        role = get_current_role()
        actor = get_current_user()

        if actor is None:
            flash("Session expired. Please login again.", "warning")
            return redirect(url_for("auth.login"))

        if role == "admin" and not actor.is_active:
            logout_actor()
            flash("Admin account is inactive.", "danger")
            return redirect(url_for("auth.login"))

        if role == "company":
            if actor.is_blacklisted or not actor.is_active:
                logout_actor()
                flash("Company account is inactive or blacklisted.", "danger")
                return redirect(url_for("auth.login"))
            if actor.approval_status != "approved":
                logout_actor()
                flash("Company account is not approved by admin.", "warning")
                return redirect(url_for("auth.login"))

        if role == "student" and (actor.is_blacklisted or not actor.is_active):
            logout_actor()
            flash("Student account is inactive or blacklisted.", "danger")
            return redirect(url_for("auth.login"))

        return view_func(*args, **kwargs)

    return wrapped_view


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in allowed_extensions


def save_resume(
    file_storage: FileStorage,
    upload_folder: str,
    allowed_extensions: set[str],
    prefix: str,
) -> str:
    if file_storage is None or file_storage.filename is None or file_storage.filename == "":
        raise ValueError("No file selected.")

    if not allowed_file(file_storage.filename, allowed_extensions):
        raise ValueError("Resume must be one of: pdf, doc, docx.")

    cleaned_name = secure_filename(file_storage.filename)
    extension = cleaned_name.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{uuid4().hex[:10]}.{extension}"

    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(os.path.join(upload_folder, filename))
    return filename


def redirect_for_role(role: str):
    if role == "admin":
        return redirect(url_for("admin.dashboard"))
    if role == "company":
        return redirect(url_for("company.dashboard"))
    if role == "student":
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("main.index"))


def parse_date(value: str, label: str):
    if not value:
        return None, f"{label} is required."
    try:
        return datetime.strptime(value, "%Y-%m-%d").date(), None
    except ValueError:
        return None, f"{label} must be in YYYY-MM-DD format."


main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
company_bp = Blueprint("company", __name__, url_prefix="/company")
student_bp = Blueprint("student", __name__, url_prefix="/student")


@main_bp.route("/")
def index():
    return redirect(url_for("auth.login"))


@main_bp.route("/resumes/<path:filename>")
@login_required
def resume_file(filename: str):
    actor = get_current_user()
    role = get_current_role()

    if role == "student":
        if actor.resume_filename != filename:
            abort(403)
    elif role not in {"admin", "company"}:
        abort(403)

    absolute_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(absolute_path):
        abort(404)

    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    actor = get_current_user()
    if actor is not None:
        return redirect_for_role(get_current_role())

    if request.method == "POST":
        role = request.form.get("role", "").strip().lower()
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not role or not identifier or not password:
            flash("All login fields are required.", "warning")
            return render_template("auth/login.html")

        if role == "admin":
            admin = Admin.query.filter(
                or_(Admin.username == identifier, Admin.email == identifier)
            ).first()
            if admin is None or not admin.check_password(password):
                flash("Invalid admin credentials.", "danger")
                return render_template("auth/login.html")
            if not admin.is_active:
                flash("Admin account is inactive.", "danger")
                return render_template("auth/login.html")

            login_actor("admin", admin.id)
            flash("Welcome, admin.", "success")
            return redirect(url_for("admin.dashboard"))

        if role == "company":
            company = Company.query.filter_by(email=identifier).first()
            if company is None or not company.check_password(password):
                flash("Invalid company credentials.", "danger")
                return render_template("auth/login.html")

            if company.approval_status == "pending":
                flash("Registration pending admin approval.", "warning")
                return render_template("auth/login.html")
            if company.approval_status == "rejected":
                flash("Company registration has been rejected by admin.", "danger")
                return render_template("auth/login.html")
            if company.is_blacklisted or not company.is_active:
                flash("Company account is inactive or blacklisted.", "danger")
                return render_template("auth/login.html")

            login_actor("company", company.id)
            flash("Company login successful.", "success")
            return redirect(url_for("company.dashboard"))

        if role == "student":
            student = Student.query.filter_by(email=identifier).first()
            if student is None or not student.check_password(password):
                flash("Invalid student credentials.", "danger")
                return render_template("auth/login.html")
            if student.is_blacklisted or not student.is_active:
                flash("Student account is inactive or blacklisted.", "danger")
                return render_template("auth/login.html")

            login_actor("student", student.id)
            flash("Student login successful.", "success")
            return redirect(url_for("student.dashboard"))

        flash("Invalid role selected.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if get_current_user() is not None:
        return redirect_for_role(get_current_role())

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        degree = request.form.get("degree", "").strip()
        branch = request.form.get("branch", "").strip()
        cgpa_raw = request.form.get("cgpa", "").strip()
        year_raw = request.form.get("graduation_year", "").strip()
        skills = request.form.get("skills", "").strip()

        if not all([full_name, roll_number, email, phone, password, confirm_password]):
            flash("Please fill all mandatory student fields.", "warning")
            return render_template("auth/register_student.html")

        if password != confirm_password:
            flash("Password and confirm password must match.", "warning")
            return render_template("auth/register_student.html")

        if Student.query.filter_by(email=email).first() is not None:
            flash("Email already exists for another student.", "danger")
            return render_template("auth/register_student.html")

        if Student.query.filter_by(roll_number=roll_number).first() is not None:
            flash("Roll number already exists.", "danger")
            return render_template("auth/register_student.html")

        if Student.query.filter_by(phone=phone).first() is not None:
            flash("Phone number already exists.", "danger")
            return render_template("auth/register_student.html")

        cgpa = None
        if cgpa_raw:
            try:
                cgpa = float(cgpa_raw)
            except ValueError:
                flash("CGPA must be a valid number.", "warning")
                return render_template("auth/register_student.html")

        graduation_year = None
        if year_raw:
            try:
                graduation_year = int(year_raw)
            except ValueError:
                flash("Graduation year must be a valid year.", "warning")
                return render_template("auth/register_student.html")

        student = Student(
            full_name=full_name,
            roll_number=roll_number,
            email=email,
            phone=phone,
            degree=degree or None,
            branch=branch or None,
            cgpa=cgpa,
            graduation_year=graduation_year,
            skills=skills or None,
        )
        student.set_password(password)

        resume = request.files.get("resume")
        if resume and resume.filename:
            try:
                student.resume_filename = save_resume(
                    resume,
                    app.config["UPLOAD_FOLDER"],
                    app.config["ALLOWED_RESUME_EXTENSIONS"],
                    f"student_{roll_number}",
                )
            except ValueError as exc:
                flash(str(exc), "warning")
                return render_template("auth/register_student.html")

        db.session.add(student)
        db.session.commit()

        flash("Student registration successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_student.html")


@auth_bp.route("/register/company", methods=["GET", "POST"])
def register_company():
    if get_current_user() is not None:
        return redirect_for_role(get_current_role())

    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        industry = request.form.get("industry", "").strip()
        hr_contact_name = request.form.get("hr_contact_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        website = request.form.get("website", "").strip()
        address = request.form.get("address", "").strip()
        description = request.form.get("description", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all(
            [company_name, industry, hr_contact_name, email, phone, password, confirm_password]
        ):
            flash("Please fill all mandatory company fields.", "warning")
            return render_template("auth/register_company.html")

        if password != confirm_password:
            flash("Password and confirm password must match.", "warning")
            return render_template("auth/register_company.html")

        if Company.query.filter_by(email=email).first() is not None:
            flash("Company email already registered.", "danger")
            return render_template("auth/register_company.html")

        company = Company(
            company_name=company_name,
            industry=industry,
            hr_contact_name=hr_contact_name,
            email=email,
            phone=phone,
            website=website or None,
            address=address or None,
            description=description or None,
            approval_status="pending",
            is_active=True,
            is_blacklisted=False,
        )
        company.set_password(password)

        db.session.add(company)
        db.session.commit()

        flash("Company registered. Wait for admin approval before login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_company.html")


@auth_bp.route("/logout")
def logout():
    logout_actor()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@admin_bp.before_request
@login_required
@role_required("admin")
@account_access_required
def protect_admin_routes():
    return None


@admin_bp.route("/dashboard")
def dashboard():
    stats = {
        "students": Student.query.count(),
        "companies": Company.query.count(),
        "drives": PlacementDrive.query.count(),
        "applications": Application.query.count(),
        "pending_companies": Company.query.filter_by(approval_status="pending").count(),
        "pending_drives": PlacementDrive.query.filter_by(status="pending").count(),
        "placements": PlacementRecord.query.count(),
        "active_students": Student.query.filter_by(is_active=True).count(),
        "active_companies": Company.query.filter_by(is_active=True).count(),
        "blacklisted_students": Student.query.filter_by(is_blacklisted=True).count(),
        "blacklisted_companies": Company.query.filter_by(is_blacklisted=True).count(),
    }
    return render_template("admin/dashboard.html", stats=stats)


@admin_bp.route("/companies")
def companies():
    search_term = request.args.get("q", "").strip()

    query = Company.query
    if search_term:
        like_expr = f"%{search_term}%"
        filters = [
            Company.company_name.ilike(like_expr),
            Company.industry.ilike(like_expr),
            Company.email.ilike(like_expr),
        ]
        if search_term.isdigit():
            filters.append(Company.id == int(search_term))
        query = query.filter(or_(*filters))

    companies_list = query.order_by(Company.created_at.desc()).all()
    return render_template(
        "admin/companies.html",
        companies=companies_list,
        search_term=search_term,
    )


@admin_bp.route("/companies/<int:company_id>/approve", methods=["POST"])
def approve_company(company_id: int):
    company = db.session.get(Company, company_id)
    if company is None:
        flash("Company not found.", "danger")
        return redirect(url_for("admin.companies"))

    company.approval_status = "approved"
    company.is_active = True
    db.session.commit()
    flash(f"Company '{company.company_name}' approved.", "success")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/companies/<int:company_id>/reject", methods=["POST"])
def reject_company(company_id: int):
    company = db.session.get(Company, company_id)
    if company is None:
        flash("Company not found.", "danger")
        return redirect(url_for("admin.companies"))

    company.approval_status = "rejected"
    db.session.commit()
    flash(f"Company '{company.company_name}' rejected.", "warning")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/companies/<int:company_id>/toggle-active", methods=["POST"])
def toggle_company_active(company_id: int):
    company = db.session.get(Company, company_id)
    if company is None:
        flash("Company not found.", "danger")
        return redirect(url_for("admin.companies"))

    company.is_active = not company.is_active
    db.session.commit()
    state = "activated" if company.is_active else "deactivated"
    flash(f"Company '{company.company_name}' {state}.", "info")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/companies/<int:company_id>/toggle-blacklist", methods=["POST"])
def toggle_company_blacklist(company_id: int):
    company = db.session.get(Company, company_id)
    if company is None:
        flash("Company not found.", "danger")
        return redirect(url_for("admin.companies"))

    company.is_blacklisted = not company.is_blacklisted
    if company.is_blacklisted:
        company.is_active = False

    db.session.commit()
    state = "blacklisted" if company.is_blacklisted else "removed from blacklist"
    flash(f"Company '{company.company_name}' {state}.", "warning")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/students")
def students():
    search_term = request.args.get("q", "").strip()

    query = Student.query
    if search_term:
        like_expr = f"%{search_term}%"
        filters = [
            Student.full_name.ilike(like_expr),
            Student.roll_number.ilike(like_expr),
            Student.email.ilike(like_expr),
            Student.phone.ilike(like_expr),
        ]
        if search_term.isdigit():
            filters.append(Student.id == int(search_term))
        query = query.filter(or_(*filters))

    students_list = query.order_by(Student.created_at.desc()).all()
    return render_template(
        "admin/students.html",
        students=students_list,
        search_term=search_term,
    )


@admin_bp.route("/students/<int:student_id>/toggle-active", methods=["POST"])
def toggle_student_active(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    student.is_active = not student.is_active
    db.session.commit()
    state = "activated" if student.is_active else "deactivated"
    flash(f"Student '{student.full_name}' {state}.", "info")
    return redirect(url_for("admin.students"))


@admin_bp.route("/students/<int:student_id>/toggle-blacklist", methods=["POST"])
def toggle_student_blacklist(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    student.is_blacklisted = not student.is_blacklisted
    if student.is_blacklisted:
        student.is_active = False

    db.session.commit()
    state = "blacklisted" if student.is_blacklisted else "removed from blacklist"
    flash(f"Student '{student.full_name}' {state}.", "warning")
    return redirect(url_for("admin.students"))


@admin_bp.route("/drives")
def drives():
    status_filter = request.args.get("status", "").strip().lower()
    timeline_filter = request.args.get("timeline", "").strip().lower()
    search_term = request.args.get("q", "").strip()

    query = PlacementDrive.query.join(Company)

    if status_filter in {"pending", "approved", "rejected", "closed"}:
        query = query.filter(PlacementDrive.status == status_filter)

    if timeline_filter == "upcoming":
        query = query.filter(
            or_(
                PlacementDrive.drive_date >= date.today(),
                db.and_(
                    PlacementDrive.drive_date.is_(None),
                    PlacementDrive.application_deadline >= date.today(),
                ),
            )
        )
    elif timeline_filter == "past":
        query = query.filter(
            or_(
                PlacementDrive.drive_date < date.today(),
                db.and_(
                    PlacementDrive.drive_date.is_(None),
                    PlacementDrive.application_deadline < date.today(),
                ),
            )
        )

    if search_term:
        like_expr = f"%{search_term}%"
        filters = [
            PlacementDrive.title.ilike(like_expr),
            Company.company_name.ilike(like_expr),
            PlacementDrive.location.ilike(like_expr),
        ]
        if search_term.isdigit():
            filters.append(PlacementDrive.id == int(search_term))
        query = query.filter(or_(*filters))

    drives_list = query.order_by(PlacementDrive.created_at.desc()).all()
    return render_template(
        "admin/drives.html",
        drives=drives_list,
        status_filter=status_filter,
        timeline_filter=timeline_filter,
        search_term=search_term,
    )


@admin_bp.route("/drives/<int:drive_id>/approve", methods=["POST"])
def approve_drive(drive_id: int):
    drive = db.session.get(PlacementDrive, drive_id)
    if drive is None:
        flash("Placement drive not found.", "danger")
        return redirect(url_for("admin.drives"))

    if drive.company.approval_status != "approved" or drive.company.is_blacklisted:
        flash("Drive cannot be approved because company is not eligible.", "warning")
        return redirect(url_for("admin.drives"))

    drive.status = "approved"
    db.session.commit()
    flash(f"Drive '{drive.title}' approved.", "success")
    return redirect(url_for("admin.drives"))


@admin_bp.route("/drives/<int:drive_id>/reject", methods=["POST"])
def reject_drive(drive_id: int):
    drive = db.session.get(PlacementDrive, drive_id)
    if drive is None:
        flash("Placement drive not found.", "danger")
        return redirect(url_for("admin.drives"))

    drive.status = "rejected"
    db.session.commit()
    flash(f"Drive '{drive.title}' rejected.", "warning")
    return redirect(url_for("admin.drives"))


@admin_bp.route("/applications")
def applications():
    status_filter = request.args.get("status", "").strip().lower()
    search_term = request.args.get("q", "").strip()

    query = Application.query.join(Student).join(PlacementDrive).join(Company)

    if status_filter in {"applied", "shortlisted", "selected", "rejected"}:
        query = query.filter(Application.status == status_filter)

    if search_term:
        like_expr = f"%{search_term}%"
        filters = [
            Student.full_name.ilike(like_expr),
            Student.roll_number.ilike(like_expr),
            PlacementDrive.title.ilike(like_expr),
            Company.company_name.ilike(like_expr),
        ]
        if search_term.isdigit():
            filters.append(Application.id == int(search_term))
        query = query.filter(or_(*filters))

    application_list = query.order_by(Application.application_date.desc()).all()
    return render_template(
        "admin/applications.html",
        applications=application_list,
        status_filter=status_filter,
        search_term=search_term,
    )


@admin_bp.route("/placements")
def placements():
    placement_list = PlacementRecord.query.order_by(PlacementRecord.placement_date.desc()).all()
    return render_template("admin/placements.html", placements=placement_list)


@company_bp.before_request
@login_required
@role_required("company")
@account_access_required
def protect_company_routes():
    return None


def current_company() -> Company:
    return get_current_user()


@company_bp.route("/dashboard", endpoint="dashboard")
def company_dashboard():
    company = current_company()
    drives = (
        PlacementDrive.query.filter_by(company_id=company.id)
        .order_by(PlacementDrive.created_at.desc())
        .all()
    )

    drive_ids = [drive.id for drive in drives]
    applicant_count_map = {}
    if drive_ids:
        rows = (
            db.session.query(Application.drive_id, func.count(Application.id))
            .filter(Application.drive_id.in_(drive_ids))
            .group_by(Application.drive_id)
            .all()
        )
        applicant_count_map = {drive_id: count for drive_id, count in rows}

    return render_template(
        "company/dashboard.html",
        company=company,
        drives=drives,
        applicant_count_map=applicant_count_map,
    )


@company_bp.route("/profile", methods=["GET", "POST"], endpoint="profile")
def company_profile():
    company = current_company()

    if request.method == "POST":
        company.company_name = request.form.get("company_name", "").strip() or company.company_name
        company.industry = request.form.get("industry", "").strip() or company.industry
        company.hr_contact_name = (
            request.form.get("hr_contact_name", "").strip() or company.hr_contact_name
        )
        company.phone = request.form.get("phone", "").strip() or company.phone
        company.website = request.form.get("website", "").strip() or None
        company.address = request.form.get("address", "").strip() or None
        company.description = request.form.get("description", "").strip() or None

        db.session.commit()
        flash("Company profile updated.", "success")
        return redirect(url_for("company.profile"))

    return render_template("company/profile.html", company=company)


@company_bp.route("/drives/new", methods=["GET", "POST"], endpoint="create_drive")
def create_drive():
    company = current_company()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        eligibility_criteria = request.form.get("eligibility_criteria", "").strip()
        required_skills = request.form.get("required_skills", "").strip()
        experience_required = request.form.get("experience_required", "").strip()
        salary_raw = request.form.get("salary_lpa", "").strip()
        location = request.form.get("location", "").strip()
        deadline_raw = request.form.get("application_deadline", "").strip()
        drive_date_raw = request.form.get("drive_date", "").strip()

        if not all([title, job_description, eligibility_criteria, deadline_raw]):
            flash("Title, description, eligibility and deadline are required.", "warning")
            return render_template("company/drive_form.html", drive=None)

        application_deadline, error = parse_date(deadline_raw, "Application deadline")
        if error:
            flash(error, "warning")
            return render_template("company/drive_form.html", drive=None)

        drive_date = None
        if drive_date_raw:
            drive_date, error = parse_date(drive_date_raw, "Drive date")
            if error:
                flash(error, "warning")
                return render_template("company/drive_form.html", drive=None)

        salary_lpa = None
        if salary_raw:
            try:
                salary_lpa = float(salary_raw)
            except ValueError:
                flash("Salary LPA must be numeric.", "warning")
                return render_template("company/drive_form.html", drive=None)

        drive = PlacementDrive(
            company_id=company.id,
            title=title,
            job_description=job_description,
            eligibility_criteria=eligibility_criteria,
            required_skills=required_skills or None,
            experience_required=experience_required or None,
            salary_lpa=salary_lpa,
            location=location or None,
            application_deadline=application_deadline,
            drive_date=drive_date,
            status="pending",
        )
        db.session.add(drive)
        db.session.commit()

        flash("Placement drive created and sent for admin approval.", "success")
        return redirect(url_for("company.dashboard"))

    return render_template("company/drive_form.html", drive=None)


@company_bp.route("/drives/<int:drive_id>/edit", methods=["GET", "POST"], endpoint="edit_drive")
def edit_drive(drive_id: int):
    company = current_company()
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        job_description = request.form.get("job_description", "").strip()
        eligibility_criteria = request.form.get("eligibility_criteria", "").strip()
        required_skills = request.form.get("required_skills", "").strip()
        experience_required = request.form.get("experience_required", "").strip()
        salary_raw = request.form.get("salary_lpa", "").strip()
        location = request.form.get("location", "").strip()
        deadline_raw = request.form.get("application_deadline", "").strip()
        drive_date_raw = request.form.get("drive_date", "").strip()

        if not all([title, job_description, eligibility_criteria, deadline_raw]):
            flash("Title, description, eligibility and deadline are required.", "warning")
            return render_template("company/drive_form.html", drive=drive)

        application_deadline, error = parse_date(deadline_raw, "Application deadline")
        if error:
            flash(error, "warning")
            return render_template("company/drive_form.html", drive=drive)

        drive_date = None
        if drive_date_raw:
            drive_date, error = parse_date(drive_date_raw, "Drive date")
            if error:
                flash(error, "warning")
                return render_template("company/drive_form.html", drive=drive)

        salary_lpa = None
        if salary_raw:
            try:
                salary_lpa = float(salary_raw)
            except ValueError:
                flash("Salary LPA must be numeric.", "warning")
                return render_template("company/drive_form.html", drive=drive)

        drive.title = title
        drive.job_description = job_description
        drive.eligibility_criteria = eligibility_criteria
        drive.required_skills = required_skills or None
        drive.experience_required = experience_required or None
        drive.salary_lpa = salary_lpa
        drive.location = location or None
        drive.application_deadline = application_deadline
        drive.drive_date = drive_date

        if drive.status in {"approved", "rejected"}:
            drive.status = "pending"

        db.session.commit()
        flash("Drive updated. It is now pending admin approval.", "success")
        return redirect(url_for("company.dashboard"))

    return render_template("company/drive_form.html", drive=drive)


@company_bp.route("/drives/<int:drive_id>/close", methods=["POST"], endpoint="close_drive")
def close_drive(drive_id: int):
    company = current_company()
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    drive.status = "closed"
    db.session.commit()
    flash(f"Drive '{drive.title}' has been closed.", "info")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/drives/<int:drive_id>/delete", methods=["POST"], endpoint="delete_drive")
def delete_drive(drive_id: int):
    company = current_company()
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    if drive.applications.count() > 0:
        flash("Cannot delete a drive that already has applications.", "warning")
        return redirect(url_for("company.dashboard"))

    db.session.delete(drive)
    db.session.commit()
    flash("Drive deleted successfully.", "success")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/drives/<int:drive_id>/applications", endpoint="drive_applications")
def drive_applications(drive_id: int):
    company = current_company()
    drive = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    status_filter = request.args.get("status", "").strip().lower()
    applications_query = drive.applications.order_by(Application.application_date.desc())
    if status_filter in {"applied", "shortlisted", "selected", "rejected"}:
        applications_query = applications_query.filter(Application.status == status_filter)

    applications = applications_query.all()
    summary = {
        "total": drive.applications.count(),
        "shortlisted": drive.applications.filter(Application.status == "shortlisted").count(),
        "selected": drive.applications.filter(Application.status == "selected").count(),
        "rejected": drive.applications.filter(Application.status == "rejected").count(),
    }

    return render_template(
        "company/drive_applications.html",
        drive=drive,
        applications=applications,
        status_filter=status_filter,
        summary=summary,
    )


@company_bp.route(
    "/applications/<int:application_id>/status",
    methods=["POST"],
    endpoint="update_application_status",
)
def update_application_status(application_id: int):
    company = current_company()
    application = Application.query.get_or_404(application_id)

    if application.drive.company_id != company.id:
        flash("You cannot update applications for another company.", "danger")
        return redirect(url_for("company.dashboard"))

    new_status = request.form.get("status", "").strip().lower()
    allowed = {"applied", "shortlisted", "selected", "rejected"}
    if new_status not in allowed:
        flash("Invalid application status.", "danger")
        return redirect(url_for("company.drive_applications", drive_id=application.drive_id))

    application.status = new_status

    if new_status == "selected":
        if application.placement is None:
            placement = PlacementRecord(
                student_id=application.student_id,
                company_id=company.id,
                drive_id=application.drive_id,
                application_id=application.id,
                designation=application.drive.title,
                package_lpa=application.drive.salary_lpa,
                placement_date=date.today(),
            )
            db.session.add(placement)
    elif application.placement is not None:
        db.session.delete(application.placement)

    db.session.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("company.drive_applications", drive_id=application.drive_id))


@student_bp.before_request
@login_required
@role_required("student")
@account_access_required
def protect_student_routes():
    return None


def current_student() -> Student:
    return get_current_user()


@student_bp.route("/dashboard", endpoint="dashboard")
def student_dashboard():
    student = current_student()

    open_drives = (
        PlacementDrive.query.join(Company)
        .filter(
            PlacementDrive.status == "approved",
            PlacementDrive.application_deadline >= date.today(),
            Company.approval_status == "approved",
            Company.is_active.is_(True),
            Company.is_blacklisted.is_(False),
        )
        .order_by(PlacementDrive.application_deadline.asc())
        .all()
    )

    applications = (
        Application.query.filter_by(student_id=student.id)
        .order_by(Application.application_date.desc())
        .all()
    )

    placements = (
        PlacementRecord.query.filter_by(student_id=student.id)
        .order_by(PlacementRecord.placement_date.desc())
        .all()
    )

    return render_template(
        "student/dashboard.html",
        student=student,
        open_drives=open_drives,
        applications=applications,
        placements=placements,
    )


@student_bp.route("/drives", endpoint="drives")
def drives_for_student():
    student = current_student()
    search_term = request.args.get("q", "").strip()

    query = PlacementDrive.query.join(Company).filter(
        PlacementDrive.status == "approved",
        PlacementDrive.application_deadline >= date.today(),
        Company.approval_status == "approved",
        Company.is_active.is_(True),
        Company.is_blacklisted.is_(False),
    )

    if search_term:
        like_expr = f"%{search_term}%"
        query = query.filter(
            or_(
                PlacementDrive.title.ilike(like_expr),
                Company.company_name.ilike(like_expr),
                PlacementDrive.required_skills.ilike(like_expr),
            )
        )

    drives_list = query.order_by(PlacementDrive.application_deadline.asc()).all()

    applied_drive_ids = {
        application.drive_id
        for application in Application.query.filter_by(student_id=student.id).all()
    }

    return render_template(
        "student/drives.html",
        drives=drives_list,
        search_term=search_term,
        applied_drive_ids=applied_drive_ids,
    )


@student_bp.route("/drives/<int:drive_id>/apply", methods=["POST"], endpoint="apply_to_drive")
def apply_to_drive(drive_id: int):
    student = current_student()
    drive = db.session.get(PlacementDrive, drive_id)

    if drive is None:
        flash("Drive not found.", "danger")
        return redirect(url_for("student.drives"))

    if not drive.is_open:
        flash("This drive is not open for applications.", "warning")
        return redirect(url_for("student.drives"))

    existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing is not None:
        flash("You have already applied to this drive.", "warning")
        return redirect(url_for("student.drives"))

    application = Application(student_id=student.id, drive_id=drive.id, status="applied")
    db.session.add(application)
    db.session.commit()

    flash("Application submitted successfully.", "success")
    return redirect(url_for("student.applications"))


@student_bp.route("/applications", endpoint="applications")
def student_applications():
    student = current_student()
    application_list = (
        Application.query.filter_by(student_id=student.id)
        .order_by(Application.application_date.desc())
        .all()
    )
    return render_template("student/applications.html", applications=application_list)


@student_bp.route("/history", endpoint="history")
def student_history():
    student = current_student()
    placements = (
        PlacementRecord.query.filter_by(student_id=student.id)
        .order_by(PlacementRecord.placement_date.desc())
        .all()
    )
    return render_template("student/history.html", placements=placements)


@student_bp.route("/profile", methods=["GET", "POST"], endpoint="profile")
def student_profile():
    student = current_student()

    if request.method == "POST":
        student.full_name = request.form.get("full_name", "").strip() or student.full_name
        student.phone = request.form.get("phone", "").strip() or student.phone
        student.degree = request.form.get("degree", "").strip() or None
        student.branch = request.form.get("branch", "").strip() or None
        student.skills = request.form.get("skills", "").strip() or None

        cgpa_raw = request.form.get("cgpa", "").strip()
        year_raw = request.form.get("graduation_year", "").strip()

        if cgpa_raw:
            try:
                student.cgpa = float(cgpa_raw)
            except ValueError:
                flash("CGPA must be a valid number.", "warning")
                return render_template("student/profile.html", student=student)
        else:
            student.cgpa = None

        if year_raw:
            try:
                student.graduation_year = int(year_raw)
            except ValueError:
                flash("Graduation year must be a valid integer.", "warning")
                return render_template("student/profile.html", student=student)
        else:
            student.graduation_year = None

        resume = request.files.get("resume")
        if resume and resume.filename:
            try:
                student.resume_filename = save_resume(
                    resume,
                    app.config["UPLOAD_FOLDER"],
                    app.config["ALLOWED_RESUME_EXTENSIONS"],
                    f"student_{student.roll_number}",
                )
            except ValueError as exc:
                flash(str(exc), "warning")
                return render_template("student/profile.html", student=student)

        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=student)


app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(company_bp)
app.register_blueprint(student_bp)


@app.before_request
def load_current_actor():
    boot_token = app.config["SESSION_BOOT_TOKEN"]
    if session.get("_boot_token") != boot_token:
        session.clear()
        session["_boot_token"] = boot_token

    g.current_role = get_current_role()
    g.current_user = get_current_user()


@app.context_processor
def inject_current_actor():
    return {
        "current_role": get_current_role(),
        "current_user": get_current_user(),
    }


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(debug=True)
