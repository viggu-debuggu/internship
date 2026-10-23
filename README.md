# Placement Portal Application (Flask + SQLite)

A full-featured role-based campus placement portal for **Admin**, **Company**, and **Student** users.

---

## 🚀 Tech Stack
- **Backend**: Python 3, Flask 3.0.3, Werkzeug
- **ORM & Database**: Flask-SQLAlchemy 3.1.1, SQLite
- **Frontend**: Jinja2 Templates, Bootstrap 5.3, Vanilla CSS

---

## 📁 Project Structure

```text
Placement-Portal-Application---V1/
├── app.py                      # Core application: models, routes, auth, utilities
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation with working URLs and setup instructions
├── .gitignore                  # Git ignore rules
├── instance/
│   ├── placement_portal.db     # Auto-generated SQLite database
│   └── uploads/resumes/        # Secure resume storage
├── static/
│   └── css/style.css           # Styling
└── templates/
    ├── base.html               # Main layout and navigation
    ├── shared/                 # Shared views
    ├── auth/                   # Login and registration templates
    ├── admin/                  # Admin management templates
    ├── company/                # Company portal templates
    └── student/                # Student portal templates
```

---

## 🌐 Working URLs & Endpoints

When running locally at `http://127.0.0.1:5000`:

### 1. General & Authentication
| Page / Action | URL | Description |
| :--- | :--- | :--- |
| **Home / Root** | `http://127.0.0.1:5000/` | Redirects to login page |
| **Unified Login** | `http://127.0.0.1:5000/auth/login` | Role-based login (Admin, Company, Student) |
| **Student Registration** | `http://127.0.0.1:5000/auth/register/student` | Sign up with Roll No, Email, and Phone |
| **Company Registration** | `http://127.0.0.1:5000/auth/register/company` | Sign up for recruiters (requires Admin approval) |
| **Logout** | `http://127.0.0.1:5000/auth/logout` | Clears active session |

---

### 2. Administrator Portal
| Page / Action | URL | Description |
| :--- | :--- | :--- |
| **Dashboard** | `http://127.0.0.1:5000/admin/dashboard` | Portal statistics (companies, students, drives, selections) |
| **Manage Companies** | `http://127.0.0.1:5000/admin/companies` | Approve/reject registrations, toggle active/blacklist status |
| **Manage Students** | `http://127.0.0.1:5000/admin/students` | View profiles, search/filter, toggle active/blacklist status |
| **Manage Drives** | `http://127.0.0.1:5000/admin/drives` | Approve or reject placement drives submitted by companies |
| **All Applications** | `http://127.0.0.1:5000/admin/applications` | Master view of all student applications |
| **Placement Records** | `http://127.0.0.1:5000/admin/placements` | Master record of placed students, CTCs, and companies |

---

### 3. Company Portal
| Page / Action | URL | Description |
| :--- | :--- | :--- |
| **Dashboard** | `http://127.0.0.1:5000/company/dashboard` | Company drive metrics and applicants |
| **Profile** | `http://127.0.0.1:5000/company/profile` | Update company description, address, website, HR contact |
| **Post New Drive** | `http://127.0.0.1:5000/company/drives/new` | Create a job posting (CTC, criteria, deadlines) |
| **Drive Applicants** | `http://127.0.0.1:5000/company/drives/<drive_id>/applications` | Review candidate resumes, shortlist, and select students |

---

### 4. Student Portal
| Page / Action | URL | Description |
| :--- | :--- | :--- |
| **Dashboard** | `http://127.0.0.1:5000/student/dashboard` | Student overview & announcements |
| **Available Drives** | `http://127.0.0.1:5000/student/drives` | Explore approved job postings and apply in 1-click |
| **My Applications** | `http://127.0.0.1:5000/student/applications` | Track application statuses (Applied, Shortlisted, Selected, Rejected) |
| **Placement History** | `http://127.0.0.1:5000/student/history` | View confirmed offers and placement details |
| **Profile & Resume** | `http://127.0.0.1:5000/student/profile` | Edit CGPA, degree, skills, and upload PDF/DOCX resume |

---

## 🔑 Default Credentials

### Administrator
- **Username / Email**: `admin` or `admin@placement.local`
- **Password**: `admin123`

---

## 💻 How to Run Locally

### Option A: Standard Python Virtual Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/viggu-debuggu/internship.git
   cd internship
   ```

2. **Create and activate a virtual environment**:
   - **macOS / Linux**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the application**:
   ```bash
   python app.py
   ```

5. **Open in browser**:
   ```text
   http://127.0.0.1:5000
   ```

### Option B: Fast setup with `uv`

```bash
uv venv
.\.venv\Scripts\activate
uv pip install -r requirements.txt
python app.py
```

---

## 🔒 Key Features & Security Notes
- **Automatic Initialization**: SQLite database and default admin account are seeded automatically on first run.
- **RBAC & Authorization**: View access restricted via `@login_required`, `@role_required`, and `@account_access_required`.
- **Duplicate Prevention**: Compound unique constraint on `(student_id, drive_id)` ensures duplicate applications cannot be submitted.
- **Secure File Uploads**: Resumes are sanitized with `secure_filename`, restricted to `.pdf`, `.doc`, `.docx` under 4 MB, and stored with UUID obfuscation.
