# Placement Portal Application (Flask + SQLite)

A role-based placement portal for **Admin**, **Company**, and **Student** users.

## Tech Stack
- Flask
- Jinja2 + HTML/CSS/Bootstrap
- SQLite

## Simplified Project Structure

```text
Placement-Portal-Application---V1/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── instance/
│   └── (auto-created DB + resume uploads)
├── static/
│   └── css/style.css
└── templates/
    ├── base.html
    ├── shared/
    ├── auth/
    ├── admin/
    ├── company/
    └── student/
```

## Run Locally

1. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run application

```bash
python app.py
```

4. Open in browser

```text
http://127.0.0.1:5000
```

## Default Admin Login
- Username: `admin`
- Password: `admin123`

## Notes
- Database is created programmatically on first run.
- Admin is seeded automatically.
- Duplicate applications for the same student-drive pair are prevented.
- Only approved companies can access company operations and create drives.
