import sqlite3
import os

import os
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'users.db'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # USERS TABLE
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT    NOT NULL,
            email     TEXT    NOT NULL UNIQUE,
            password  TEXT    NOT NULL,
            role      TEXT    NOT NULL CHECK(role IN ('jobseeker','recruiter')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # JOBS TABLE (posted by recruiters)
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            recruiter_id INTEGER NOT NULL,
            title       TEXT NOT NULL,
            company     TEXT NOT NULL,
            location    TEXT,
            description TEXT NOT NULL,
            skills      TEXT,
            posted_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recruiter_id) REFERENCES users(id)
        )
    ''')

    # APPLICATIONS TABLE (seeker applies to a job)
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id       INTEGER NOT NULL,
            seeker_id    INTEGER NOT NULL,
            resume_text  TEXT,
            ai_score     REAL DEFAULT 0,
            skills_found TEXT,
            status       TEXT DEFAULT 'pending' CHECK(status IN ('pending','shortlisted','rejected')),
            applied_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id)    REFERENCES jobs(id),
            FOREIGN KEY (seeker_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()

# ── USER HELPERS ────────────────────────────────────────────
def create_user(name, email, password_hash, role):
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?,?,?,?)',
            (name, email, password_hash, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False          # duplicate email
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user

def get_user_by_id(uid):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    conn.close()
    return user

# ── JOB HELPERS ─────────────────────────────────────────────
def create_job(recruiter_id, title, company, location, description, skills):
    conn = get_db()
    conn.execute(
        'INSERT INTO jobs (recruiter_id,title,company,location,description,skills) VALUES (?,?,?,?,?,?)',
        (recruiter_id, title, company, location, description, skills)
    )
    conn.commit()
    conn.close()

def get_all_jobs():
    conn = get_db()
    jobs = conn.execute('''
        SELECT j.*, u.name AS recruiter_name
        FROM jobs j JOIN users u ON j.recruiter_id = u.id
        ORDER BY j.posted_at DESC
    ''').fetchall()
    conn.close()
    return jobs

def get_jobs_by_recruiter(recruiter_id):
    conn = get_db()
    jobs = conn.execute(
        'SELECT * FROM jobs WHERE recruiter_id = ? ORDER BY posted_at DESC',
        (recruiter_id,)
    ).fetchall()
    conn.close()
    return jobs

def get_job_by_id(job_id):
    conn = get_db()
    job = conn.execute('SELECT * FROM jobs WHERE id = ?', (job_id,)).fetchone()
    conn.close()
    return job

def delete_job(job_id, recruiter_id):
    conn = get_db()
    conn.execute('DELETE FROM jobs WHERE id = ? AND recruiter_id = ?', (job_id, recruiter_id))
    conn.commit()
    conn.close()

# ── APPLICATION HELPERS ──────────────────────────────────────
def apply_to_job(job_id, seeker_id, resume_text, ai_score, skills_found):
    conn = get_db()
    # prevent duplicate applications
    existing = conn.execute(
        'SELECT id FROM applications WHERE job_id=? AND seeker_id=?',
        (job_id, seeker_id)
    ).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        'INSERT INTO applications (job_id,seeker_id,resume_text,ai_score,skills_found) VALUES (?,?,?,?,?)',
        (job_id, seeker_id, resume_text, ai_score, skills_found)
    )
    conn.commit()
    conn.close()
    return True

def get_applications_by_seeker(seeker_id):
    conn = get_db()
    apps = conn.execute('''
        SELECT a.*, j.title AS job_title, j.company, j.location
        FROM applications a JOIN jobs j ON a.job_id = j.id
        WHERE a.seeker_id = ?
        ORDER BY a.applied_at DESC
    ''', (seeker_id,)).fetchall()
    conn.close()
    return apps

def get_applications_by_job(job_id):
    conn = get_db()
    apps = conn.execute('''
        SELECT a.*, u.name AS seeker_name, u.email AS seeker_email
        FROM applications a JOIN users u ON a.seeker_id = u.id
        WHERE a.job_id = ?
        ORDER BY a.ai_score DESC
    ''', (job_id,)).fetchall()
    conn.close()
    return apps

def update_application_status(app_id, status):
    conn = get_db()
    conn.execute('UPDATE applications SET status=? WHERE id=?', (status, app_id))
    conn.commit()
    conn.close()

# ── ADMIN HELPERS ────────────────────────────────────────────
def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users

def get_all_applications():
    conn = get_db()
    apps = conn.execute('''
        SELECT a.id, u.name AS seeker, j.title AS job, j.company,
               a.ai_score, a.status, a.applied_at
        FROM applications a
        JOIN users u ON a.seeker_id = u.id
        JOIN jobs  j ON a.job_id    = j.id
        ORDER BY a.applied_at DESC
    ''').fetchall()
    conn.close()
    return apps
