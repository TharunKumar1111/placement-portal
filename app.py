from flask import Flask, render_template, request, redirect, session, send_from_directory, flash, Response
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "placementportal"

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def calculate_resume_score(filename):

    score = 0

    keywords = [
        'html', 'css', 'javascript', 'python', 'flask',
        'sql', 'sqlite', 'react', 'git', 'github'
    ]

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        with open(filepath, 'r', errors='ignore') as file:
            content = file.read().lower()

            for keyword in keywords:
                if keyword in content:
                    score += 10

    except:
        score = 50

    return score


def calculate_skill_match(student_skills, job_role):

    if not student_skills:
        return 0

    skills = student_skills.lower().split(',')
    job_role = job_role.lower()

    matched = 0

    for skill in skills:
        skill = skill.strip()

        if skill and skill in job_role:
            matched += 1

    percentage = int((matched / len(skills)) * 100)

    return percentage


def get_deadline_status(deadline):

    today = datetime.now().date()
    deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()

    days_left = (deadline_date - today).days

    if days_left < 0:
        return "Closed"
    elif days_left <= 7:
        return "Closing Soon"
    else:
        return "Open"
def add_notification(student_id, message):

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO notifications(
            student_id,
            message,
            created_at
        )
        VALUES(?,?,?)
        ''',
        (
            student_id,
            message,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )

    conn.commit()
    conn.close()


def init_db():

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS students(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    try:
        cur.execute("ALTER TABLE students ADD COLUMN skills TEXT")
    except:
        pass
    try:
        cur.execute("ALTER TABLE students ADD COLUMN profile_photo TEXT")
    except:
        pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role TEXT,
            package TEXT,
            logo TEXT,
            deadline TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            student_id INTEGER,
            status TEXT DEFAULT 'Pending',
            resume TEXT,
            applied_date TEXT
        )
    ''')

    try:
        cur.execute("ALTER TABLE applications ADD COLUMN resume_score INTEGER")
    except:
        pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS saved_jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            job_id INTEGER
        )
    ''')
    cur.execute('''
                 CREATE TABLE IF NOT EXISTS interviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        interview_date TEXT,
        interview_time TEXT,
        meeting_link TEXT,
        status TEXT DEFAULT 'Scheduled'
    )
''')

    cur.execute("SELECT * FROM jobs")
    data = cur.fetchall()

    if len(data) == 0:

        cur.execute('''
            INSERT INTO jobs(company, role, package, logo, deadline)
            VALUES(?,?,?,?,?)
        ''', ("Google", "Frontend Developer", "12 LPA", "google.png", "2026-06-30"))

        cur.execute('''
            INSERT INTO jobs(company, role, package, logo, deadline)
            VALUES(?,?,?,?,?)
        ''', ("Amazon", "Web Developer", "10 LPA", "amazon.png", "2026-07-10"))

        cur.execute('''
            INSERT INTO jobs(company, role, package, logo, deadline)
            VALUES(?,?,?,?,?)
        ''', ("Infosys", "Software Engineer", "6 LPA", "infosys.png", "2026-07-20"))
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        message TEXT,
        created_at TEXT
    )
''')
       

    conn.commit()
    conn.close()


init_db()


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_student():

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO students(name,email,password) VALUES(?,?,?)",
        (name, email, password)
    )

    conn.commit()
    conn.close()

    return redirect('/')


@app.route('/login', methods=['POST'])
def login():

    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM students WHERE email=? AND password=?",
        (email, password)
    )

    user = cur.fetchone()
    conn.close()

    if user:
        session['student_id'] = user[0]
        session['student_name'] = user[1]
        return redirect('/dashboard')

    return render_template(
        'login.html',
        error="Invalid Email or Password"
    )


@app.route('/dashboard')
def dashboard():

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM applications WHERE student_id=?",
        (student_id,)
    )
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM jobs")
    jobs_count = cur.fetchone()[0]

    cur.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT 3")
    recent_jobs = cur.fetchall()

    cur.execute('''
        SELECT company, COUNT(*) as total
        FROM jobs
        GROUP BY company
        ORDER BY total DESC
        LIMIT 5
    ''')
    top_companies = cur.fetchall()

    cur.execute(
        "SELECT skills FROM students WHERE id=?",
        (student_id,)
    )

    result = cur.fetchone()
    student_skills = result[0] if result else ""

    recommended_jobs = []

    if student_skills:

        skills_list = student_skills.split(',')

        for skill in skills_list:

            skill = skill.strip()

            cur.execute('''
                SELECT *
                FROM jobs
                WHERE role LIKE ?
                OR company LIKE ?
                LIMIT 3
            ''', ('%' + skill + '%', '%' + skill + '%'))

            recommended_jobs.extend(cur.fetchall())
    cur.execute(
    '''
    SELECT profile_photo
    FROM students
    WHERE id = ?
    ''',
    (student_id,))
    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None
    placement_percentage = 0
    if jobs_count > 0:
        placement_percentage = int((total / jobs_count) * 100)
    conn.close()

    return render_template(
        'dashboard.html',
        name=session['student_name'],
        total=total,
        jobs_count=jobs_count,
        recent_jobs=recent_jobs,
        top_companies=top_companies,
        recommended_jobs=recommended_jobs,
        profile_photo=profile_photo,
        placement_percentage=placement_percentage
    )


@app.route('/jobs')
def jobs():

    if 'student_id' not in session:
        return redirect('/')

    search = request.args.get('search')
    company_filter = request.args.get('company')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT company FROM jobs")
    companies = cur.fetchall()

    if search and company_filter:

        cur.execute('''
            SELECT jobs.*, COUNT(applications.id)
            FROM jobs
            LEFT JOIN applications
            ON jobs.id = applications.job_id
            WHERE
            (
                company LIKE ?
                OR role LIKE ?
                OR package LIKE ?
                OR deadline LIKE ?
            )
            AND company = ?
            GROUP BY jobs.id
        ''', (
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%',
            company_filter
        ))

    elif search:

        cur.execute('''
            SELECT jobs.*, COUNT(applications.id)
            FROM jobs
            LEFT JOIN applications
            ON jobs.id = applications.job_id
            WHERE company LIKE ?
            OR role LIKE ?
            OR package LIKE ?
            OR deadline LIKE ?
            GROUP BY jobs.id
        ''', (
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%'
        ))

    elif company_filter:

        cur.execute('''
            SELECT jobs.*, COUNT(applications.id)
            FROM jobs
            LEFT JOIN applications
            ON jobs.id = applications.job_id
            WHERE company = ?
            GROUP BY jobs.id
        ''', (company_filter,))

    else:

        cur.execute('''
            SELECT jobs.*, COUNT(applications.id)
            FROM jobs
            LEFT JOIN applications
            ON jobs.id = applications.job_id
            GROUP BY jobs.id
        ''')

    jobs = cur.fetchall()

    cur.execute(
        "SELECT skills FROM students WHERE id=?",
        (session['student_id'],)
    )

    student_data = cur.fetchone()
    student_skills = student_data[0] if student_data else ""

    cur.execute(
        '''
        SELECT job_id
        FROM applications
        WHERE student_id = ?
        ''',
        (session['student_id'],)
    )

    applied_jobs = [row[0] for row in cur.fetchall()]

    jobs_with_match = []

    for job in jobs:

        match = calculate_skill_match(student_skills, job[2])

        deadline_status = get_deadline_status(job[5])

        already_applied = job[0] in applied_jobs

        job = job + (match, deadline_status, already_applied)

        jobs_with_match.append(job)

    jobs = jobs_with_match
    cur.execute(
    '''
    SELECT profile_photo
    FROM students
    WHERE id = ?
    ''',
    (session['student_id'],))
    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None

    conn.close()

    return render_template(
        'jobs.html',
        jobs=jobs,
        companies=companies,
        profile_photo=profile_photo
    )

@app.route('/job_details/<int:id>')
def job_details(id):

    if 'student_id' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT jobs.*, COUNT(applications.id)
        FROM jobs
        LEFT JOIN applications
        ON jobs.id = applications.job_id
        WHERE jobs.id = ?
        GROUP BY jobs.id
    ''', (id,))

    job = cur.fetchone()
    conn.close()

    return render_template(
        'job_details.html',
        job=job
    )


@app.route('/save_job/<int:id>')
def save_job(id):

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT *
        FROM saved_jobs
        WHERE student_id = ?
        AND job_id = ?
    ''', (student_id, id))

    already_saved = cur.fetchone()

    if already_saved:
        conn.close()
        flash("Job already saved")
        return redirect('/jobs')

    cur.execute(
        "INSERT INTO saved_jobs(student_id, job_id) VALUES(?,?)",
        (student_id, id)
    )

    conn.commit()
    conn.close()

    flash("Job saved successfully")

    return redirect('/jobs')


@app.route('/saved_jobs')
def saved_jobs():

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT jobs.*
        FROM saved_jobs
        JOIN jobs
        ON saved_jobs.job_id = jobs.id
        WHERE saved_jobs.student_id = ?
    ''', (student_id,))

    jobs = cur.fetchall()
    cur.execute(
    '''
    SELECT profile_photo
    FROM students
    WHERE id = ?
    ''',
    (session['student_id'],))
    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None
    conn.close()

    return render_template(
        'saved_jobs.html',
        jobs=jobs,
        profile_photo=profile_photo
    )


@app.route('/remove_saved_job/<int:id>')
def remove_saved_job(id):

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        DELETE FROM saved_jobs
        WHERE job_id = ?
        AND student_id = ?
    ''', (id, student_id))

    conn.commit()
    conn.close()

    flash("Saved job removed")

    return redirect('/saved_jobs')


@app.route('/apply', methods=['POST'])
def apply():

    if 'student_id' not in session:
        return redirect('/')

    job_id = request.form['job_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "SELECT deadline FROM jobs WHERE id=?",
        (job_id,)
    )

    deadline = cur.fetchone()[0]

    if get_deadline_status(deadline) == "Closed":

        conn.close()

        flash("Application deadline is closed")

        return redirect('/jobs')

    student_id = session['student_id']

    resume = request.files['resume']

    filename = resume.filename

    resume.save(
        os.path.join(
            app.config['UPLOAD_FOLDER'],
            filename
        )
    )

    cur.execute(
        "SELECT * FROM applications WHERE job_id=? AND student_id=?",
        (job_id, student_id)
    )

    already_applied = cur.fetchone()

    if already_applied:

        conn.close()

        flash("You already applied for this job")

        return redirect('/jobs')

    applied_date = datetime.now().strftime("%Y-%m-%d")

    resume_score = calculate_resume_score(filename)

    cur.execute('''
        INSERT INTO applications(
            job_id,
            student_id,
            resume,
            applied_date,
            resume_score
        )
        VALUES(?,?,?,?,?)
    ''', (
        job_id,
        student_id,
        filename,
        applied_date,
        resume_score
    ))

    conn.commit()
    add_notification(
    student_id,
    "Application submitted successfully"
)
    conn.close()

    flash("Application submitted successfully")

    return redirect('/my_applications')
@app.route('/my_applications')
def my_applications():

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT jobs.company,
               jobs.role,
               jobs.package,
               applications.status,
               applications.resume,
               applications.applied_date,
               applications.resume_score,
               applications.id
        FROM applications
        JOIN jobs
        ON applications.job_id = jobs.id
        WHERE applications.student_id = ?
    ''', (student_id,))

    jobs = cur.fetchall()
    cur.execute(
    '''
    SELECT profile_photo
    FROM students
    WHERE id = ?
    ''',
    (session['student_id'],))
    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None
    conn.close()

    return render_template(
        'my_applications.html',
        jobs=jobs,
        profile_photo=profile_photo
    )


@app.route('/withdraw_application/<int:id>')
def withdraw_application(id):

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        DELETE FROM applications
        WHERE id = ?
        AND student_id = ?
    ''', (id, student_id))

    conn.commit()
    conn.close()

    flash("Application withdrawn successfully")

    return redirect('/my_applications')


@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if request.method == 'POST':

        skills = request.form['skills']

        photo = request.files.get('profile_photo')

        if photo and photo.filename != "":

            filename = photo.filename

            photo.save(
                os.path.join(
                    'static/profile_photos',
                    filename
                )
            )

            cur.execute(
                '''
                UPDATE students
                SET skills=?,
                    profile_photo=?
                WHERE id=?
                ''',
                (skills, filename, student_id)
            )

        else:

            cur.execute(
                '''
                UPDATE students
                SET skills=?
                WHERE id=?
                ''',
                (skills, student_id)
            )

        conn.commit()

        flash('Skills updated successfully')

    cur.execute(
        "SELECT * FROM students WHERE id=?",
        (student_id,)
    )

    student = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) FROM applications WHERE student_id=?",
        (student_id,)
    )

    total = cur.fetchone()[0]
    cur.execute(
    '''
    SELECT profile_photo
    FROM students
    WHERE id = ?
    ''',
    (session['student_id'],))
    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None
    conn.close()

    return render_template(
        'profile.html',
        student=student,
        total=total,
        profile_photo=profile_photo
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')


@app.route('/admin_login', methods=['POST'])
def admin_login_post():

    username = request.form['username']
    password = request.form['password']

    if username == "admin" and password == "admin123":
        session['admin'] = True
        return redirect('/admin')

    return "Invalid Admin Credentials"


@app.route('/admin_logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin_login')


@app.route('/admin')
def admin():

    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM jobs")
    jobs = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications")
    total_applications = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE status='Pending'")
    pending_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE status='Selected'")
    selected_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM applications WHERE status='Rejected'")
    rejected_count = cur.fetchone()[0]

    conn.close()

    return render_template(
        'admin.html',
        jobs=jobs,
        total_students=total_students,
        total_jobs=total_jobs,
        total_applications=total_applications,
        pending_count=pending_count,
        selected_count=selected_count,
        rejected_count=rejected_count
    )


@app.route('/add_job', methods=['POST'])
def add_job():

    if 'admin' not in session:
        return redirect('/admin_login')

    company = request.form['company']
    role = request.form['role']
    package = request.form['package']
    deadline = request.form['deadline']

    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename != "":
        logo = logo_file.filename
        logo_file.save(
        os.path.join(
            'static/logos',
            logo
        )
    )
    else:
        logo = "google.png"

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO jobs(company, role, package, logo, deadline)
        VALUES(?,?,?,?,?)
    ''', (company, role, package, logo, deadline))

    conn.commit()
    conn.close()

    return redirect('/admin')


@app.route('/delete_job/<int:id>')
def delete_job(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM jobs WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect('/admin')


@app.route('/edit_job/<int:id>', methods=['GET', 'POST'])
def edit_job(id):

    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    if request.method == 'POST':

        company = request.form['company']
        role = request.form['role']
        package = request.form['package']
        deadline = request.form['deadline']

        cur.execute('''
            UPDATE jobs
            SET company=?,
                role=?,
                package=?,
                deadline=?
            WHERE id=?
        ''', (company, role, package, deadline, id))

        conn.commit()
        conn.close()

        return redirect('/admin')

    cur.execute(
        "SELECT * FROM jobs WHERE id=?",
        (id,)
    )

    job = cur.fetchone()
    conn.close()

    return render_template(
        'edit_job.html',
        job=job
    )


@app.route('/applicants')
def applicants():

    if 'admin' not in session:
        return redirect('/admin_login')

    status_filter = request.args.get('status')
    search = request.args.get('search')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    query = '''
        SELECT students.name,
               students.email,
               students.skills,
               jobs.company,
               jobs.role,
               applications.resume,
               applications.status,
               applications.applied_date,
               applications.resume_score,
               applications.id
        FROM applications
        JOIN students
        ON applications.student_id = students.id
        JOIN jobs
        ON applications.job_id = jobs.id
        WHERE 1=1
    '''

    params = []

    if status_filter:
        query += " AND applications.status = ?"
        params.append(status_filter)

    if search:
        query += '''
            AND (
                students.name LIKE ?
                OR students.email LIKE ?
                OR jobs.company LIKE ?
                OR jobs.role LIKE ?
            )
        '''
        params.extend([
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%',
            '%' + search + '%'
        ])

    cur.execute(query, params)

    applicants = cur.fetchall()
    conn.close()

    return render_template(
        'applicants.html',
        applicants=applicants
    )


@app.route('/update_status', methods=['POST'])
def update_status():

    if 'admin' not in session:
        return redirect('/admin_login')

    application_id = request.form['application_id']
    status = request.form['status']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT student_id
        FROM applications
        WHERE id = ?
        ''',
        (application_id,)
    )

    student_id = cur.fetchone()[0]

    cur.execute(
        '''
        UPDATE applications
        SET status = ?
        WHERE id = ?
        ''',
        (status, application_id)
    )

    conn.commit()
    conn.close()

    add_notification(
        student_id,
        f"Application status changed to {status}"
    )

    return redirect('/applicants')
@app.route('/schedule_interview', methods=['POST'])
def schedule_interview():

    if 'admin' not in session:
        return redirect('/admin_login')

    application_id = request.form['application_id']
    interview_date = request.form['interview_date']
    interview_time = request.form['interview_time']
    meeting_link = request.form['meeting_link']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO interviews(
            application_id,
            interview_date,
            interview_time,
            meeting_link
        )
        VALUES(?,?,?,?)
        ''',
        (
            application_id,
            interview_date,
            interview_time,
            meeting_link
        )
    )

    conn.commit()
    cur.execute(
    '''
    SELECT student_id
    FROM applications
    WHERE id = ?
    ''',
    (application_id,))
    student_id = cur.fetchone()[0]
    conn.close()
    add_notification(student_id,
    f"Interview scheduled on {interview_date} at {interview_time}"
)

    flash("Interview scheduled successfully")

    return redirect('/applicants')


@app.route('/export_applicants')
def export_applicants():

    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT students.name,
               students.email,
               students.skills,
               jobs.company,
               jobs.role,
               applications.status,
               applications.resume,
               applications.applied_date,
               applications.resume_score
        FROM applications
        JOIN students
        ON applications.student_id = students.id
        JOIN jobs
        ON applications.job_id = jobs.id
    ''')

    applicants = cur.fetchall()
    conn.close()

    csv_data = "Name,Email,Skills,Company,Role,Status,Resume,Applied Date,Resume Score\n"

    for app_data in applicants:
        csv_data += f"{app_data[0]},{app_data[1]},{app_data[2]},{app_data[3]},{app_data[4]},{app_data[5]},{app_data[6]},{app_data[7]},{app_data[8]}\n"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment;filename=applicants.csv"
        }
    )


@app.route('/uploads/<filename>')
def uploaded_file(filename):

    if 'admin' not in session:
        return redirect('/admin_login')

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )


@app.route('/download_resume/<filename>')
def download_resume(filename):

    if 'admin' not in session:
        return redirect('/admin_login')

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )
@app.route('/interviews')
def interviews():

    if 'student_id' not in session:
        return redirect('/')

    student_id = session['student_id']

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute('''
        SELECT jobs.company,
               jobs.role,
               interviews.interview_date,
               interviews.interview_time,
               interviews.meeting_link,
               interviews.status
        FROM interviews
        JOIN applications
        ON interviews.application_id = applications.id
        JOIN jobs
        ON applications.job_id = jobs.id
        WHERE applications.student_id = ?
    ''', (student_id,))

    interviews = cur.fetchall()

    cur.execute(
        "SELECT profile_photo FROM students WHERE id=?",
        (student_id,)
    )

    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None

    conn.close()

    return render_template(
        'interviews.html',
        interviews=interviews,
        profile_photo=profile_photo
    )
@app.route('/notifications')
def notifications():

    if 'student_id' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT message, created_at
        FROM notifications
        WHERE student_id = ?
        ORDER BY id DESC
        ''',
        (session['student_id'],)
    )

    notifications = cur.fetchall()

    cur.execute(
        "SELECT profile_photo FROM students WHERE id=?",
        (session['student_id'],)
    )

    photo_data = cur.fetchone()
    profile_photo = photo_data[0] if photo_data else None

    conn.close()

    return render_template(
        'notifications.html',
        notifications=notifications,
        profile_photo=profile_photo
    )


if __name__ == '__main__':
    app.run(debug=True)