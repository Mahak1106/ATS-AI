import random
from re import search
from flask import Flask, render_template, request, session, redirect, send_from_directory
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from streamlit import status
from werkzeug.utils import secure_filename

app = Flask(__name__)
def send_email(to_email, subject, message):

    sender_email = "yourgmail@gmail.com"
    sender_password = "YOUR_APP_PASSWORD"

    msg = MIMEText(message)

    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    server = smtplib.SMTP('smtp.gmail.com', 587)

    server.starttls()

    server.login(
        sender_email,
        sender_password
    )

    server.send_message(msg)

    server.quit()

app.secret_key = "ats_secret_key"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 5")
    jobs = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        name=session['name'],
        role=session['role'],
        total_jobs=total_jobs,
        total_users=total_users,
        total_applications=total_applications,
        jobs=jobs
    )


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, password, role)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            session['name'] = user[1]
            session['role'] = user[4]

            return redirect('/dashboard')

        return "Invalid Email or Password"

    return render_template('login.html')


@app.route('/add_job', methods=['GET', 'POST'])
def add_job():

    if request.method == 'POST':

        title = request.form['title']
        company = request.form['company']
        description = request.form['description']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO jobs (title, company, description) VALUES (?, ?, ?)",
            (title, company, description)
        )

        conn.commit()
        conn.close()

        return redirect('/jobs')

    return render_template('add_job.html')


@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM jobs WHERE id=?",
        (job_id,)
    )

    job = cursor.fetchone()

    if request.method == 'POST':

        cursor.execute(
            """
            INSERT INTO applications
            (applicant_name, job_title)
            VALUES (?, ?)
            """,
            (session['name'], job[1])
        )

        conn.commit()
        conn.close()

        return redirect('/applications')

    conn.close()

    return render_template(
        'apply.html',
        job=job
    )

@app.route('/applications')
def applications():

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM applications WHERE applicant_name=?",
        (session['name'],)
    )

    applications = cursor.fetchall()

    conn.close()

    return render_template(
        'applications.html',
        applications=applications
    )


@app.route('/upload_resume', methods=['GET', 'POST'])
def upload_resume():

    if request.method == 'POST':

        file = request.files['resume']

        if file:

            filename = secure_filename(file.filename)
            score = random.randint(70, 98)
            file.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO resumes
                (applicant_name, filename, score)
                VALUES (?,?,?)
                """,
                (session['name'], filename, score)
            )
           
            conn.commit()
            conn.close()

        return redirect('/dashboard')

    return render_template('upload_resume.html')


@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

@app.route('/recruiter_dashboard')
def recruiter_dashboard():

    if 'name' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Total Jobs
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    # Total Users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # Total Applications
    cursor.execute("SELECT COUNT(*) FROM applications")
    total_applications = cursor.fetchone()[0]

    # Shortlisted Candidates
    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE status='Shortlisted'"
    )
    shortlisted = cursor.fetchone()[0]

    # All Applications
    search = request.args.get('search', '')

    if search:
       cursor.execute(
           """
           SELECT * FROM applications
           WHERE applicant_name LIKE ?
           """,
    
        (f'%{search}%',)
        )
    else:
        cursor.execute("SELECT * FROM applications")
 
    applications = cursor.fetchall()

    conn.close()

    return render_template(
        'recruiter_dashboard.html',
        total_jobs=total_jobs,
        total_users=total_users,
        total_applications=total_applications,
        shortlisted=shortlisted,
        applications=applications,
        search=search
    )

@app.route('/update_status/<int:app_id>/<status>')
def update_status(app_id, status):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Update Status
    cursor.execute(
        """
        UPDATE applications
        SET status = ?
        WHERE id = ?
        """,
        (status, app_id)
    )

    # Get Candidate Details
    cursor.execute(
        """
        SELECT
            users.email,
            applications.job_title,
            applications.applicant_name
        FROM applications
        JOIN users
            ON users.name = applications.applicant_name
        WHERE applications.id = ?
        """,
        (app_id,)
    )

    candidate = cursor.fetchone()

    conn.commit()
    conn.close()

    # Send Email Notification
    if candidate:

        email = candidate[0]
        job_title = candidate[1]
        applicant_name = candidate[2]

        subject = f"ATS.AI - Application Status Update"

        message = f"""
Hello {applicant_name},

Your application for the position:

{job_title}

has been updated.

Current Status: {status}

Thank you for using ATS.AI.

Best Regards,
ATS.AI Recruitment Team
"""

        try:

            send_email(
                email,
                subject,
                message
            )

        except Exception as e:

            print("Email Error:", e)

    return redirect('/recruiter_dashboard')


@app.route('/ai_ranking')
def ai_ranking():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT applicant_name, filename, score
        FROM resumes
        ORDER BY score DESC
    """)

    candidates = cursor.fetchall()

    conn.close()

    return render_template(
        'ai_ranking.html',
        candidates=candidates
    )

@app.route('/view_resumes')
def view_resumes():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM resumes")

    resumes = cursor.fetchall()

    conn.close()

    return render_template(
        'view_resumes.html',
        resumes=resumes
    )

@app.route('/download_resume/<filename>')
def download_resume(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )

@app.route('/job_details/<int:job_id>')
def job_details(job_id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM jobs WHERE id=?",
        (job_id,)
    )

    job = cursor.fetchone()

    conn.close()

    return render_template(
        'job_details.html',
        job=job
    )

@app.route('/jobs')
def jobs():

    search = request.args.get('search', '')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if search:
        cursor.execute(
            """
            SELECT * FROM jobs
            WHERE title LIKE ?
            OR company LIKE ?
            """,
            (f'%{search}%', f'%{search}%')
        )
    else:
        cursor.execute("SELECT * FROM jobs")

    jobs = cursor.fetchall()

    conn.close()

    return render_template(
        'jobs.html',
        jobs=jobs
    )

@app.route('/view_resume/<filename>')
def view_resume(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )

@app.route('/schedule_interview/<int:app_id>', methods=['GET', 'POST'])
def schedule_interview(app_id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT applicant_name, job_title FROM applications WHERE id=?",
        (app_id,)
    )

    application = cursor.fetchone()

    if request.method == 'POST':

        interview_date = request.form['date']
        interview_time = request.form['time']
        interview_mode = request.form['mode']

        cursor.execute(
            """
            INSERT INTO interviews
            (
                candidate_name,
                job_title,
                interview_date,
                interview_time,
                interview_mode
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                application[0],
                application[1],
                interview_date,
                interview_time,
                interview_mode
            )
        )

        conn.commit()
        conn.close()

        return redirect('/recruiter_dashboard')

    conn.close()

    return render_template(
        'schedule_interview.html',
        application=application
    )

@app.route('/interviews')
def interviews():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM interviews
        ORDER BY interview_date ASC
        """
    )

    interviews = cursor.fetchall()

    conn.close()

    return render_template(
        'interviews.html',
        interviews=interviews
    )

if __name__ == '__main__':
    app.run(debug=True)