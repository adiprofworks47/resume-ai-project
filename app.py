import PyPDF2
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from model import calculate_similarity, extract_skills, matching_skills
from database import (
    init_db, create_user, get_user_by_email, get_user_by_id,
    create_job, get_all_jobs, get_jobs_by_recruiter, get_job_by_id, delete_job,
    apply_to_job, get_applications_by_seeker, get_applications_by_job,
    update_application_status,
    get_all_users, get_all_applications
)

app = Flask(__name__)
app.secret_key = 'resumeai-secret-key-change-in-production'

with app.app_context():
    init_db()

JOBS = {
    "Data Scientist":  "Python machine learning data analysis pandas numpy statistics",
    "Web Developer":   "HTML CSS JavaScript Flask frontend backend react",
    "Java Developer":  "Java Spring backend OOP microservices",
    "AI Engineer":     "machine learning deep learning python tensorflow neural networks",
    "Cloud Engineer":  "AWS cloud docker kubernetes networking devops"
}

def extract_text_from_pdf(file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
    except Exception:
        pass
    return text

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def seeker_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'jobseeker':
            flash('Access restricted to job seekers.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def recruiter_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'recruiter':
            flash('Access restricted to recruiters.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('seeker') if session['role'] == 'jobseeker' else url_for('recruiter'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user     = get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name']    = user['name']
            session['role']    = user['role']
            return redirect(url_for('seeker') if user['role'] == 'jobseeker' else url_for('recruiter'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        role     = request.form.get('role', 'jobseeker')
        if not name or not email or not password:
            flash('All fields are required.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        else:
            hashed = generate_password_hash(password)
            ok = create_user(name, email, hashed, role)
            if ok:
                flash('Account created! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('An account with that email already exists.', 'error')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/seeker')
@login_required
@seeker_required
def seeker():
    jobs = get_all_jobs()
    applications = get_applications_by_seeker(session['user_id'])
    return render_template('seeker_dashboard.html',
        jobs=jobs, applications=applications, tab='browse')

@app.route('/seeker/analyze', methods=['POST'])
@login_required
@seeker_required
def seeker_analyze():
    resume_text     = request.form.get('resume', '')
    job_description = request.form.get('job_desc', '')
    uploaded_file   = request.files.get('resume_file')
    if uploaded_file and uploaded_file.filename:
        resume_text = extract_text_from_pdf(uploaded_file)
    recommendations = {}
    skills  = []
    matched = []
    if resume_text and job_description:
        for role, desc in JOBS.items():
            recommendations[role] = calculate_similarity(resume_text, desc)
        recommendations = dict(sorted(recommendations.items(), key=lambda x: x[1], reverse=True))
        skills  = extract_skills(resume_text)
        matched = matching_skills(resume_text, job_description)
    jobs = get_all_jobs()
    applications = get_applications_by_seeker(session['user_id'])
    return render_template('seeker_dashboard.html',
        jobs=jobs, applications=applications,
        recommendations=recommendations, skills=skills, matched=matched,
        resume_text=resume_text, job_description=job_description, tab='analyze')

@app.route('/seeker/apply/<int:job_id>', methods=['POST'])
@login_required
@seeker_required
def apply(job_id):
    resume_text = request.form.get('resume_text', '')
    job = get_job_by_id(job_id)
    if not job:
        flash('Job not found.', 'error')
        return redirect(url_for('seeker'))
    if not resume_text.strip():
        flash('Please paste your resume before applying.', 'error')
        return redirect(url_for('seeker'))
    score  = calculate_similarity(resume_text, job['description'])
    skills = ', '.join(extract_skills(resume_text))
    ok = apply_to_job(job_id, session['user_id'], resume_text, score, skills)
    if ok:
        flash(f'Applied to "{job["title"]}" at {job["company"]}! AI match: {score}%', 'success')
    else:
        flash('You have already applied to this job.', 'error')
    return redirect(url_for('seeker'))


@app.route('/recruiter')
@login_required
@recruiter_required
def recruiter():
    jobs = get_jobs_by_recruiter(session['user_id'])
    return render_template('recruiter_dashboard.html', jobs=jobs, tab='jobs')

@app.route('/recruiter/post', methods=['POST'])
@login_required
@recruiter_required
def post_job():
    title       = request.form.get('title', '').strip()
    company     = request.form.get('company', '').strip()
    location    = request.form.get('location', '').strip()
    description = request.form.get('description', '').strip()
    skills      = request.form.get('skills', '').strip()
    if not title or not company or not description:
        flash('Title, company and description are required.', 'error')
    else:
        create_job(session['user_id'], title, company, location, description, skills)
        flash(f'"{title}" posted successfully!', 'success')
    return redirect(url_for('recruiter'))

@app.route('/recruiter/job/<int:job_id>')
@login_required
@recruiter_required
def view_applicants(job_id):
    job = get_job_by_id(job_id)
    if not job or job['recruiter_id'] != session['user_id']:
        flash('Job not found.', 'error')
        return redirect(url_for('recruiter'))
    applicants = get_applications_by_job(job_id)
    jobs = get_jobs_by_recruiter(session['user_id'])
    return render_template('recruiter_dashboard.html',
        jobs=jobs, selected_job=job, applicants=applicants, tab='applicants')

@app.route('/recruiter/job/<int:job_id>/delete', methods=['POST'])
@login_required
@recruiter_required
def delete_job_route(job_id):
    delete_job(job_id, session['user_id'])
    flash('Job deleted.', 'success')
    return redirect(url_for('recruiter'))

@app.route('/recruiter/application/<int:app_id>/status', methods=['POST'])
@login_required
@recruiter_required
def update_status(app_id):
    status = request.form.get('status', 'pending')
    job_id = request.form.get('job_id')
    update_application_status(app_id, status)
    flash('Candidate status updated.', 'success')
    return redirect(url_for('view_applicants', job_id=job_id))


@app.route('/admin')
def admin():
    try:
        users        = get_all_users()
        jobs         = get_all_jobs()
        applications = get_all_applications()
        return render_template('admin.html', users=users, jobs=jobs, applications=applications)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
