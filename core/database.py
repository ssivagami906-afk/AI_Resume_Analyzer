import sqlite3
import hashlib
import os
import datetime
import uuid
import random
import string

DB_FILE = os.path.join("data", "app_database.db")

def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table (HR Accounts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            hr_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            job_title TEXT NOT NULL,
            qualifications TEXT NOT NULL,
            is_published INTEGER DEFAULT 0,
            publish_schedule TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Applications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            candidate_key TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            candidate_name TEXT NOT NULL,
            candidate_contact TEXT NOT NULL,
            approved INTEGER NOT NULL,
            ai_reason TEXT,
            resubmit_status TEXT,
            resubmit_reason TEXT,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    """)
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(company_name: str, hr_name: str, email: str, password: str):
    init_db()
    email_clean = email.strip().lower()
    pass_hash = hash_password(password)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (company_name, hr_name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (company_name.strip(), hr_name.strip(), email_clean, pass_hash, now_str)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return True, {"id": user_id, "company_name": company_name, "hr_name": hr_name, "email": email_clean}
    except sqlite3.IntegrityError:
        conn.close()
        return False, "An account with this email address already exists. Please log in."
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {str(e)}"

def authenticate_user(email: str, password: str):
    init_db()
    email_clean = email.strip().lower()
    pass_hash = hash_password(password)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name, hr_name, email FROM users WHERE email = ? AND password_hash = ?", (email_clean, pass_hash))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def create_job(user_id: int, job_title: str, qualifications: str):
    init_db()
    job_id = f"JOB-{str(uuid.uuid4())[:8].upper()}"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO jobs (id, user_id, job_title, qualifications, is_published, publish_schedule, created_at) VALUES (?, ?, ?, ?, 0, NULL, ?)",
        (job_id, user_id, job_title.strip(), qualifications.strip(), now_str)
    )
    conn.commit()
    conn.close()
    return job_id

def get_user_jobs(user_id: int):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_job_by_id(job_id: str):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.*, u.company_name, u.hr_name 
        FROM jobs j 
        JOIN users u ON j.user_id = u.id 
        WHERE j.id = ?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_job_details(job_id: str, job_title: str, qualifications: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET job_title = ?, qualifications = ? WHERE id = ?", (job_title.strip(), qualifications.strip(), job_id))
    conn.commit()
    conn.close()

def update_job_publishing(job_id: str, is_published: bool, publish_schedule: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET is_published = ?, publish_schedule = ? WHERE id = ?", (1 if is_published else 0, publish_schedule, job_id))
    conn.commit()
    conn.close()

def generate_unique_key():
    chars = string.ascii_uppercase + string.digits
    return f"KEY-{''.join(random.choices(chars, k=6))}"

def save_application(job_id: str, candidate_name: str, candidate_contact: str, ai_result: dict, existing_key: str = None):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    contact_clean = candidate_contact.strip().lower()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    approved = 1 if ai_result.get("approved") else 0
    reason = ai_result.get("reason", "")

    if existing_key:
        candidate_key = existing_key
        cursor.execute("""
            UPDATE applications 
            SET candidate_name = ?, approved = ?, ai_reason = ?, resubmit_status = NULL, resubmit_reason = NULL, submitted_at = ?
            WHERE candidate_key = ? AND job_id = ?
        """, (candidate_name.strip(), approved, reason, now_str, candidate_key, job_id))
    else:
        candidate_key = generate_unique_key()
        cursor.execute("SELECT candidate_key FROM applications WHERE candidate_key = ?", (candidate_key,))
        while cursor.fetchone():
            candidate_key = generate_unique_key()
            cursor.execute("SELECT candidate_key FROM applications WHERE candidate_key = ?", (candidate_key,))
            
        cursor.execute("""
            INSERT INTO applications (candidate_key, job_id, candidate_name, candidate_contact, approved, ai_reason, resubmit_status, resubmit_reason, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        """, (candidate_key, job_id, candidate_name.strip(), contact_clean, approved, reason, now_str))

    conn.commit()
    conn.close()
    return candidate_key

def get_application_by_contact(job_id: str, candidate_contact: str):
    init_db()
    contact_clean = candidate_contact.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE job_id = ? AND candidate_contact = ?", (job_id, contact_clean))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_job_applications(job_id: str):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE job_id = ? ORDER BY submitted_at DESC", (job_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_application_by_key(candidate_key: str):
    init_db()
    key_clean = candidate_key.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, j.job_title, j.is_published, j.publish_schedule, u.company_name 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        JOIN users u ON j.user_id = u.id 
        WHERE a.candidate_key = ?
    """, (key_clean,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_applications_by_contact_all(contact: str):
    init_db()
    contact_clean = contact.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, j.job_title, u.company_name 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        JOIN users u ON j.user_id = u.id 
        WHERE a.candidate_contact = ?
        ORDER BY a.submitted_at DESC
    """, (contact_clean,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def set_resubmit_request(candidate_key: str, reason: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET resubmit_status = 'requested', resubmit_reason = ? WHERE candidate_key = ?", (reason.strip(), candidate_key.strip().upper()))
    conn.commit()
    conn.close()

def update_resubmit_status(candidate_key: str, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET resubmit_status = ? WHERE candidate_key = ?", (status, candidate_key.strip().upper()))
    conn.commit()
    conn.close()
