from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
import random
import string
from datetime import datetime, timedelta, time
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, time, timedelta, date
app = Flask(__name__)

# Configuration
app.secret_key = 'your_secret_key_here'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Saniya@2005'
app.config['MYSQL_DB'] = 'hospital_management'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}

mysql = MySQL(app)

# Helper functions
def generate_random_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def get_user_type():
    if 'loggedin' in session:
        return session.get('user_type')
    return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_time_slots(start_time_str="09:00", end_time_str="17:00", interval_minutes=30):
    """Generate time slots between start and end times at given intervals.
    
    Args:
        start_time_str: Start time as string (format: HH:MM)
        end_time_str: End time as string (format: HH:MM)
        interval_minutes: Time slot interval in minutes
    
    Returns:
        List of time slots formatted as strings (HH:MM)
    """
    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()
    
    slots = []
    current = datetime.combine(date.today(), start_time)
    end = datetime.combine(date.today(), end_time)
    
    while current <= end:
        slots.append(current.time().strftime('%H:%M'))
        current += timedelta(minutes=interval_minutes)
    
    return slots

# Routes
@app.route('/')
def index():
    # Debug print to see session status
    print("Current session:", session)
    
    if 'loggedin' in session:
        user_type = session.get('user_type')
        if user_type == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif user_type == 'patient':
            return redirect(url_for('patient_dashboard'))
    
    # If not logged in, stay on login page
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_input = request.form['password']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute("SELECT * FROM patients WHERE email=%s", (email,))
            user = cursor.fetchone()
            user_type = 'patient'
            
            if user is None:
                cursor.execute("SELECT * FROM doctors WHERE email=%s", (email,))
                user = cursor.fetchone()
                user_type = 'doctor'
                if user is None:
                    flash("Email not registered", "danger")
                    return redirect(url_for('login'))
            
            # Verify password (use check_password_hash if you hashed passwords)
            if password_input == user['password']:  # or check_password_hash(user['password'], password_input)
                session.clear()  # Clear any existing session
                session['loggedin'] = True
                session['id'] = user['id']
                session['email'] = user['email']
                session['user_name'] = user['name']
                session['user_type'] = user_type
                
                if user_type == 'doctor':
                    return redirect(url_for('doctor_dashboard'))
                else:
                    return redirect(url_for('patient_dashboard'))
            else:
                flash("Wrong password", "danger")
                return redirect(url_for('login'))
        finally:
            cursor.close()
    
    # If GET request or any error, show login page
    return render_template('login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        user_type = request.form.get('user_type')
        
        if not all([name, email, phone, password, confirm_password, user_type]):
            flash('Please fill all the required fields!', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        try:
            table = 'doctors' if user_type == 'doctor' else 'patients'
            cursor.execute(f'SELECT * FROM {table} WHERE email = %s', (email,))
            account = cursor.fetchone()
            
            if account:
                flash('Email already exists!', 'danger')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)

            if user_type == 'doctor':
                degree = request.form.get('degree')
                specialization = request.form.get('specialization')
                experience = request.form.get('experience')
                
                if not all([degree, specialization, experience]):
                    flash('Please fill all doctor-specific fields!', 'danger')
                    return redirect(url_for('register'))
                
                cursor.execute('''
                    INSERT INTO doctors 
                    (name, email, phone, password, degree, specialization, experience) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (name, email, phone, hashed_password, degree, specialization, experience))
            else:
                dob = request.form.get('dob')
                gender = request.form.get('gender')
                address = request.form.get('address')
                
                if not all([dob, gender, address]):
                    flash('Please fill all patient-specific fields!', 'danger')
                    return redirect(url_for('register'))
                
                cursor.execute('''
                    INSERT INTO patients 
                    (name, email, phone, password, dob, gender, address) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (name, email, phone, hashed_password, dob, gender, address))
            
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error during registration: {str(e)}', 'danger')
            return redirect(url_for('register'))
        finally:
            cursor.close()
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()  # This completely clears the session
    return redirect(url_for('login'))

# Doctor Routes
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect('/login')  # redirect if not logged in or not a doctor

    # Normal dashboard rendering logic here
    return render_template('doctor_dashboard.html')


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT a.*, p.name as patient_name 
            FROM appointments a 
            JOIN patients p ON a.patient_id = p.id 
            WHERE a.doctor_id = %s AND a.appointment_date >= CURDATE() 
            ORDER BY a.appointment_date, a.appointment_time 
            LIMIT 5
        ''', (session['id'],))
        appointments = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT patient_id) as total_patients 
            FROM appointments 
            WHERE doctor_id = %s
        ''', (session['id'],))
        total_patients = cursor.fetchone()['total_patients']
        
        cursor.execute('''
            SELECT COUNT(*) as today_appointments 
            FROM appointments 
            WHERE doctor_id = %s AND appointment_date = CURDATE()
        ''', (session['id'],))
        today_appointments = cursor.fetchone()['today_appointments']
        
        return render_template('doctor_dashboard.html', 
                            appointments=appointments, 
                            total_patients=total_patients,
                            today_appointments=today_appointments)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()
@app.route('/doctor/reports')
def doctor_reports():
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT r.*, p.name as patient_name, 
                   DATE_FORMAT(r.report_date, '%%Y-%%m-%%d') as formatted_date
            FROM reports r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.doctor_id = %s
            ORDER BY r.report_date DESC
        ''', (session['id'],))
        reports = cursor.fetchall()

        return render_template('doctor_reports.html', reports=reports)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

@app.route('/doctor/appointments')
def doctor_appointments():
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT a.*, p.name as patient_name, 
                   DATE_FORMAT(a.appointment_date, '%%Y-%%m-%%d') as formatted_date,
                   TIME_FORMAT(a.appointment_time, '%%H:%%i') as formatted_time
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.doctor_id = %s
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['id'],))
        appointments = cursor.fetchall()

        return render_template('doctor_appointments.html', 
                            appointments=appointments,
                            today=date.today().strftime('%Y-%m-%d'))
    except Exception as e:
        flash(f'Error loading appointments: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

@app.route('/doctor/appointment/<int:appointment_id>')
def doctor_appointment_details(appointment_id):
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT a.*, p.name as patient_name, p.email as patient_email, 
                   p.phone as patient_phone, p.dob as patient_dob,
                   DATE_FORMAT(a.appointment_date, '%%d %%b %%Y') as display_date,
                   TIME_FORMAT(a.appointment_time, '%%h:%%i %%p') as display_time
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.id = %s AND a.doctor_id = %s
        ''', (appointment_id, session['id']))
        appointment = cursor.fetchone()

        if not appointment:
            flash('Appointment not found', 'danger')
            return redirect(url_for('doctor_appointments'))

        return render_template('doctor_appointment_details.html', 
                            appointment=appointment)
    except Exception as e:
        flash(f'Error loading appointment: {str(e)}', 'danger')
        return redirect(url_for('doctor_appointments'))
    finally:
        cursor.close()

# ROUTE: View all doctor appointments with optional filters
@app.route('/doctor/appointments')
def view_doctor_appointments():
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    status_filter = request.args.get('status')
    date_filter = request.args.get('date')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        query = '''
            SELECT a.*, p.name as patient_name,
                   DATE_FORMAT(a.appointment_date, '%%Y-%%m-%%d') as formatted_date,
                   TIME_FORMAT(a.appointment_time, '%%H:%%i') as formatted_time
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.doctor_id = %s
        '''
        params = [session['id']]

        if status_filter:
            query += ' AND a.status = %s'
            params.append(status_filter)
        if date_filter:
            query += ' AND a.appointment_date = %s'
            params.append(date_filter)

        query += ' ORDER BY a.appointment_date DESC, a.appointment_time DESC LIMIT %s OFFSET %s'
        params.extend([per_page, (page - 1) * per_page])

        cursor.execute(query, params)
        appointments = cursor.fetchall()

        return render_template('doctor_appointments.html',
                               appointments=appointments,
                               today=date.today().strftime('%Y-%m-%d'),
                               status_filter=status_filter,
                               date_filter=date_filter)
    except Exception as e:
        flash(f'Error loading appointments: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()


# ROUTE: View details of a specific appointment
@app.route('/doctor/appointment/<int:appointment_id>')
def view_doctor_appointment_details(appointment_id):
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT a.*, p.name as patient_name, p.email as patient_email, 
                   p.phone as patient_phone, p.dob as patient_dob,
                   DATE_FORMAT(a.appointment_date, '%%d %%b %%Y') as display_date,
                   TIME_FORMAT(a.appointment_time, '%%h:%%i %%p') as display_time
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.id = %s AND a.doctor_id = %s
        ''', (appointment_id, session['id']))
        appointment = cursor.fetchone()

        if not appointment:
            flash('Appointment not found', 'danger')
            return redirect(url_for('view_doctor_appointments'))

        cursor.execute('''
            SELECT * FROM reports
            WHERE patient_id = %s
            ORDER BY report_date DESC
            LIMIT 5
        ''', (appointment['patient_id'],))
        reports = cursor.fetchall()

        return render_template('doctor_appointment_details.html',
                               appointment=appointment,
                               reports=reports)
    except Exception as e:
        flash(f'Error loading appointment: {str(e)}', 'danger')
        return redirect(url_for('view_doctor_appointments'))
    finally:
        cursor.close()


# ROUTE: Mark appointment as completed
@app.route('/doctor/appointment/<int:appointment_id>/complete', methods=['POST'])
def complete_doctor_appointment(appointment_id):
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    notes = request.form.get('notes', '')
    cursor = mysql.connection.cursor()
    try:
        cursor.execute('''
            UPDATE appointments 
            SET status = 'Completed', notes = %s, completed_at = NOW()
            WHERE id = %s AND doctor_id = %s
        ''', (notes, appointment_id, session['id']))
        mysql.connection.commit()
        flash('Appointment marked as completed', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error completing appointment: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('view_doctor_appointment_details', appointment_id=appointment_id))


# ROUTE: Cancel appointment
@app.route('/doctor/appointment/<int:appointment_id>/cancel', methods=['POST'])
def cancel_doctor_appointment(appointment_id):
    if 'loggedin' not in session or session.get('user_type') != 'doctor':
        return redirect(url_for('login'))

    cancel_reason = request.form.get('cancel_reason', '')
    cursor = mysql.connection.cursor()
    try:
        cursor.execute('''
            UPDATE appointments 
            SET status = 'Cancelled', cancel_reason = %s, canceled_at = NOW()
            WHERE id = %s AND doctor_id = %s
        ''', (cancel_reason, appointment_id, session['id']))
        mysql.connection.commit()
        flash('Appointment canceled', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error canceling appointment: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('view_doctor_appointment_details', appointment_id=appointment_id))

    
    return redirect(url_for('doctor_appointment_details', appointment_id=appointment_id))
@app.route('/doctor/patients')
def doctor_patients():
    if 'loggedin' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT p.*, COUNT(a.id) as appointment_count 
            FROM patients p 
            JOIN appointments a ON p.id = a.patient_id 
            WHERE a.doctor_id = %s 
            GROUP BY p.id
        ''', (session['id'],))
        patients = cursor.fetchall()
        
        return render_template('doctor_patients.html', patients=patients)
    except Exception as e:
        flash(f'Error loading patients: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

@app.route('/doctor/patient/<int:patient_id>')
def doctor_patient_details(patient_id):
    if 'loggedin' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('SELECT * FROM patients WHERE id = %s', (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            flash('Patient not found!', 'danger')
            return redirect(url_for('doctor_patients'))
        
        cursor.execute('''
            SELECT * FROM appointments 
            WHERE patient_id = %s AND doctor_id = %s 
            ORDER BY appointment_date DESC, appointment_time DESC
        ''', (patient_id, session['id']))
        appointments = cursor.fetchall()
        
        cursor.execute('''
            SELECT r.* FROM reports r
            WHERE r.patient_id = %s AND r.doctor_id = %s
            ORDER BY r.report_date DESC
        ''', (patient_id, session['id']))
        reports = cursor.fetchall()

        cursor.execute('''
            SELECT * FROM health_metrics 
            WHERE patient_id = %s 
            ORDER BY record_date DESC, record_time DESC
            LIMIT 10
        ''', (patient_id,))
        health_metrics = cursor.fetchall()
        
        return render_template('doctor_patient_details.html', 
                            patient=patient, 
                            appointments=appointments,
                            reports=reports,
                            health_metrics=health_metrics)
    except Exception as e:
        flash(f'Error loading patient details: {str(e)}', 'danger')
        return redirect(url_for('doctor_patients'))
    finally:
        cursor.close()

@app.route('/doctor/report/<int:report_id>')
def doctor_report_details(report_id):
    if 'loggedin' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT r.*, p.name AS patient_name
            FROM reports r
            JOIN patients p ON r.patient_id = p.id
            WHERE r.id = %s AND r.doctor_id = %s
        ''', (report_id, session['id']))
        report = cursor.fetchone()

        if not report:
            flash('Report not found or access denied!', 'danger')
            return redirect(url_for('doctor_dashboard'))
        
        return render_template('doctor_report_details.html', report=report)
    except Exception as e:
        flash(f'Error loading report: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():
    if 'loggedin' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            degree = request.form.get('degree')
            specialization = request.form.get('specialization')
            experience = request.form.get('experience')
            bio = request.form.get('bio')
            
            if not all([name, email, phone, degree, specialization, experience]):
                flash('Please fill all required fields!', 'danger')
                return redirect(url_for('doctor_profile'))
            
            cursor.execute('SELECT id FROM doctors WHERE email = %s AND id != %s', (email, session['id']))
            if cursor.fetchone():
                flash('Email already in use by another doctor!', 'danger')
                return redirect(url_for('doctor_profile'))
            
            cursor.execute('''
                UPDATE doctors SET 
                name = %s, email = %s, phone = %s, degree = %s, 
                specialization = %s, experience = %s, bio = %s 
                WHERE id = %s
            ''', (name, email, phone, degree, specialization, experience, bio, session['id']))
            mysql.connection.commit()
            
            session['user_name'] = name
            session['email'] = email
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('doctor_profile'))
        
        cursor.execute('SELECT * FROM doctors WHERE id = %s', (session['id'],))
        doctor = cursor.fetchone()
        
        return render_template('doctor_profile.html', doctor=doctor)
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

@app.route('/doctor/notifications')
def doctor_notifications():
    if 'loggedin' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT * FROM notifications 
            WHERE user_id = %s AND user_type = 'doctor'
            ORDER BY created_at DESC
        ''', (session['id'],))
        notifications = cursor.fetchall()
        
        return render_template('doctor_notifications.html', notifications=notifications)
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))
    finally:
        cursor.close()

# Patient Routes
@app.route('/patient/dashboard')
def patient_dashboard():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT a.*, d.name as doctor_name, d.specialization,
                   TIME_FORMAT(a.appointment_time, '%%H:%%i') as formatted_time,
                   DATE_FORMAT(a.appointment_date, '%%d %%b %%Y') as formatted_date
            FROM appointments a 
            JOIN doctors d ON a.doctor_id = d.id 
            WHERE a.patient_id = %s AND a.appointment_date >= CURDATE() 
            ORDER BY a.appointment_date, a.appointment_time 
            LIMIT 3
        ''', (session['id'],))
        appointments = cursor.fetchall()
        
        cursor.execute('''
            SELECT r.*, d.name as doctor_name,
                   DATE_FORMAT(r.report_date, '%%d %%b %%Y') as formatted_date
            FROM reports r
            LEFT JOIN doctors d ON r.doctor_id = d.id
            WHERE r.patient_id = %s
            ORDER BY r.report_date DESC
            LIMIT 3
        ''', (session['id'],))
        reports = cursor.fetchall()

        cursor.execute('''
            SELECT *, 
                   DATE_FORMAT(record_date, '%%d %%b %%Y') as formatted_date,
                   TIME_FORMAT(record_time, '%%H:%%i') as formatted_time
            FROM health_metrics 
            WHERE patient_id = %s 
            ORDER BY record_date DESC, record_time DESC 
            LIMIT 5
        ''', (session['id'],))
        health_metrics = cursor.fetchall()
        
        return render_template('patient_dashboard.html', 
                            appointments=appointments,
                            reports=reports,
                            health_metrics=health_metrics)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('login'))
    finally:
        cursor.close()

@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            dob = request.form.get('dob')
            gender = request.form.get('gender')
            address = request.form.get('address')
            blood_group = request.form.get('blood_group')
            
            if not all([name, email, phone, dob, gender, address]):
                flash('Please fill all required fields!', 'danger')
                return redirect(url_for('patient_profile'))
            
            cursor.execute('SELECT id FROM patients WHERE email = %s AND id != %s', (email, session['id']))
            if cursor.fetchone():
                flash('Email already in use by another patient!', 'danger')
                return redirect(url_for('patient_profile'))
            
            cursor.execute('''
                UPDATE patients SET 
                name = %s, email = %s, phone = %s, dob = %s, 
                gender = %s, address = %s, blood_group = %s 
                WHERE id = %s
            ''', (name, email, phone, dob, gender, address, blood_group, session['id']))
            mysql.connection.commit()
            
            session['user_name'] = name
            session['email'] = email
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient_profile'))
        
        cursor.execute('SELECT * FROM patients WHERE id = %s', (session['id'],))
        patient = cursor.fetchone()
        
        return render_template('patient_profile.html', patient=patient)
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()
@app.route('/patient/appointments', methods=['GET', 'POST'])
def patient_appointments():
    if 'loggedin' not in session or session.get('user_type') != 'patient':
        flash('Please login as patient first!', 'danger')
        return redirect(url_for('index'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        if request.method == 'POST':
            required_fields = ['doctor_id', 'appointment_date', 'appointment_time', 'reason']
            if not all(field in request.form and request.form[field] for field in required_fields):
                flash('Please fill in all required fields!', 'danger')
                return redirect(url_for('patient_appointments'))

            doctor_id = request.form['doctor_id']
            appointment_date = request.form['appointment_date']
            appointment_time = request.form['appointment_time']
            reason = request.form['reason']

            cursor.execute('SELECT id FROM doctors WHERE id = %s AND status = "active"', (doctor_id,))
            if not cursor.fetchone():
                flash('Invalid or inactive doctor selected!', 'danger')
                return redirect(url_for('patient_appointments'))

            try:
                appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
                if appointment_date_obj < date.today():
                    flash('Appointment date cannot be in the past!', 'danger')
                    return redirect(url_for('patient_appointments'))
            except ValueError:
                flash('Invalid date format! Use YYYY-MM-DD.', 'danger')
                return redirect(url_for('patient_appointments'))

            try:
                time_obj = datetime.strptime(appointment_time, '%H:%M').time()
                if time_obj < time(9, 0) or time_obj > time(17, 0):
                    flash('Appointments must be between 09:00 and 17:00.', 'danger')
                    return redirect(url_for('patient_appointments'))
            except ValueError:
                flash('Invalid time format! Use HH:MM.', 'danger')
                return redirect(url_for('patient_appointments'))

            cursor.execute('''
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (session['id'], doctor_id, appointment_date, appointment_time, reason))
            mysql.connection.commit()

            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient_appointments'))

        # GET request
        cursor.execute('''
            SELECT 
                a.*, 
                d.name as doctor_name, 
                d.specialization,
                DATE_FORMAT(a.appointment_date, '%%Y-%%m-%%d') as date_for_input,
                DATE_FORMAT(a.appointment_date, '%%d %%b %%Y') as formatted_date,
                TIME_FORMAT(a.appointment_time, '%%H:%%i') as time_for_input,
                TIME_FORMAT(a.appointment_time, '%%h:%%i %%p') as formatted_time
            FROM appointments a 
            JOIN doctors d ON a.doctor_id = d.id 
            WHERE a.patient_id = %s 
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        ''', (session['id'],))
        appointments = cursor.fetchall()

        cursor.execute('SELECT id, name, specialization FROM doctors WHERE status = "active" ORDER BY name')
        doctors = cursor.fetchall()

        time_slots = generate_time_slots()

        return render_template('patient_appointments.html',
                               appointments=appointments,
                               doctors=doctors,
                               time_slots=time_slots,
                               today=date.today().strftime('%Y-%m-%d'),
                               min_date=date.today().strftime('%Y-%m-%d'))

    except Exception as e:
        mysql.connection.rollback()
        app.logger.error(f'Error in patient_appointments: {str(e)}', exc_info=True)
        flash(f'An unexpected error occurred: {str(e)}', 'danger')
        return redirect(url_for('doctor_dashboard'))

    finally:
        cursor.close()
@app.route('/patient/reports')
def patient_reports():
    if 'loggedin' not in session or session.get('user_type') != 'patient':
        flash('Please login as patient first!', 'danger')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Fetch reports for logged-in patient, join with doctors to get doctor name
        cursor.execute('''
            SELECT r.id, r.report_type, r.file_path, r.upload_date, d.name as doctor_name
            FROM reports r
            JOIN doctors d ON r.doctor_id = d.id
            WHERE r.patient_id = %s
            ORDER BY r.upload_date DESC
        ''', (session['id'],))

        reports = cursor.fetchall()

        # Format upload_date nicely (optional)
        for report in reports:
            report['formatted_date'] = report['upload_date'].strftime('%d %b %Y')

    finally:
        cursor.close()

    return render_template('patient_reports.html', reports=reports)


@app.route('/patient/report/<int:report_id>')
def patient_report_details(report_id):
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT 
                r.id,
                r.report_date,
                r.diagnosis,
                r.prescription,
                r.notes,
                d.name AS doctor_name,
                DATE_FORMAT(r.report_date, '%%d %%b %%Y') AS formatted_date
            FROM reports r
            LEFT JOIN doctors d ON r.doctor_id = d.id
            WHERE r.id = %s AND r.patient_id = %s
        ''', (report_id, session['id']))
        
        report = cursor.fetchone()

        if not report:
            flash("Report not found or you are not authorized to view it.", "warning")
            return redirect(url_for("patient_reports"))

        return render_template('patient_report_details.html', report=report)

    except Exception as e:
        flash(f'Error loading report: {str(e)}', 'danger')
        return redirect(url_for('patient_reports'))

    finally:
        cursor.close()

@app.route('/patient/upload-report', methods=['GET', 'POST'])
def patient_upload_report():
    if 'loggedin' not in session or session.get('user_type') != 'patient':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    try:
        cursor.execute('SELECT id, name FROM doctors')
        doctors = cursor.fetchall()

        if request.method == 'POST':
            doctor_id = request.form.get('doctor_id')
            report_type = request.form.get('report_type')
            file = request.files.get('report_file')

            if not doctor_id or not report_type or not file:
                flash('Please fill all required fields.', 'danger')
                return render_template('patient_upload_report.html', doctors=doctors)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)

                filepath_for_db = filepath.replace("\\", "/")

                cursor.execute('''
                    INSERT INTO reports 
                    (patient_id, doctor_id, report_type, file_path, upload_date, report_date)
                    VALUES (%s, %s, %s, %s, CURDATE(), CURDATE())
                    ''', (
                    session['id'],
                    doctor_id,
                    report_type,
                    filepath_for_db
            ))


                mysql.connection.commit()
                flash('Report uploaded successfully!', 'success')
                return redirect(url_for('patient_reports'))
            else:
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, PDF, DOC, DOCX.', 'danger')

        return render_template('patient_upload_report.html', doctors=doctors)

    except Exception as e:
        flash(f'Error uploading report: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))

    finally:
        cursor.close()

@app.route('/patient/bills')
def patient_bills():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT b.*, d.name as doctor_name 
            FROM bills b 
            JOIN appointments a ON b.appointment_id = a.id 
            JOIN doctors d ON a.doctor_id = d.id 
            WHERE a.patient_id = %s 
            ORDER BY b.issue_date DESC
        ''', (session['id'],))
        bills = cursor.fetchall()
        
        return render_template('patient_bills.html', bills=bills)
    except Exception as e:
        flash(f'Error loading bills: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/doctors')
def patient_doctors():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT id, name, specialization, experience, bio 
            FROM doctors 
            ORDER BY name
        ''')
        doctors = cursor.fetchall()
        
        return render_template('patient_doctors.html', doctors=doctors)
    except Exception as e:
        flash(f'Error loading doctors: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/health-metrics', methods=['GET', 'POST'])
def patient_health_metrics():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        if request.method == 'POST':
            systolic = request.form.get('systolic')
            diastolic = request.form.get('diastolic')
            sugar = request.form.get('sugar')
            weight = request.form.get('weight')
            notes = request.form.get('notes')

            if not all([systolic, diastolic, sugar, weight]):
                flash('Please fill all required fields!', 'danger')
                return redirect(url_for('patient_health_metrics'))

            cursor.execute('''
                INSERT INTO health_metrics 
                (patient_id, systolic, diastolic, sugar, weight, notes, record_date, record_time)
                VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), CURTIME())
            ''', (session['id'], systolic, diastolic, sugar, weight, notes))
            mysql.connection.commit()
            flash('Health metrics recorded successfully!', 'success')
            return redirect(url_for('patient_health_metrics'))

        cursor.execute('''
            SELECT *, 
            DATE_FORMAT(record_date, '%%d %%b %%Y') as formatted_date 
            FROM health_metrics 
            WHERE patient_id = %s 
            ORDER BY record_date DESC, record_time DESC
        ''', (session['id'],))
        metrics = cursor.fetchall()

        dates = [m['formatted_date'] for m in metrics]
        systolic_data = [m['systolic'] for m in metrics]
        diastolic_data = [m['diastolic'] for m in metrics]
        sugar_data = [m['sugar'] for m in metrics]
        weight_data = [m['weight'] for m in metrics]

        return render_template(
            'patient_health_metrics.html', 
            metrics=metrics,
            dates=dates[::-1],
            systolic_data=systolic_data[::-1],
            diastolic_data=diastolic_data[::-1],
            sugar_data=sugar_data[::-1],
            weight_data=weight_data[::-1]
        )

    except Exception as e:
        flash(f'Error managing health metrics: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/feedback', methods=['GET', 'POST'])
def patient_feedback():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        if request.method == 'POST':
            doctor_id = request.form.get('doctor_id')
            rating = request.form.get('rating')
            comments = request.form.get('comments')
            
            if not all([doctor_id, rating]):
                flash('Please fill all required fields!', 'danger')
                return redirect(url_for('patient_feedback'))
            
            cursor.execute('''
                INSERT INTO feedback 
                (patient_id, doctor_id, rating, comments, feedback_date) 
                VALUES (%s, %s, %s, %s, CURDATE())
            ''', (session['id'], doctor_id, rating, comments))
            mysql.connection.commit()
            
            flash('Feedback submitted successfully!', 'success')
            return redirect(url_for('patient_feedback'))
        
        cursor.execute('''
            SELECT f.*, d.name as doctor_name 
            FROM feedback f 
            JOIN doctors d ON f.doctor_id = d.id 
            WHERE f.patient_id = %s 
            ORDER BY f.feedback_date DESC
        ''', (session['id'],))
        feedbacks = cursor.fetchall()
        
        cursor.execute('SELECT id, name FROM doctors ORDER BY name')
        doctors = cursor.fetchall()
        
        return render_template('patient_feedback.html', 
                            feedbacks=feedbacks,
                            doctors=doctors)
    except Exception as e:
        flash(f'Error managing feedback: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/attachments', methods=['GET', 'POST'])
def patient_attachments():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file selected!', 'danger')
                return redirect(url_for('patient_attachments'))
            
            file = request.files['file']
            description = request.form.get('description', '')
            
            if file.filename == '':
                flash('No file selected!', 'danger')
                return redirect(url_for('patient_attachments'))
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                
                cursor.execute('''
                    INSERT INTO attachments 
                    (patient_id, file_name, file_path, description, upload_date) 
                    VALUES (%s, %s, %s, %s, CURDATE())
                ''', (session['id'], filename, filepath, description))
                mysql.connection.commit()
                
                flash('File uploaded successfully!', 'success')
                return redirect(url_for('patient_attachments'))
            else:
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, PDF, DOC, DOCX.', 'danger')
        
        cursor.execute('''
            SELECT * FROM attachments 
            WHERE patient_id = %s 
            ORDER BY upload_date DESC
        ''', (session['id'],))
        attachments = cursor.fetchall()
        
        return render_template('patient_attachments.html', attachments=attachments)
    except Exception as e:
        flash(f'Error managing attachments: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/notifications')
def patient_notifications():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        cursor.execute('''
            SELECT * FROM notifications 
            WHERE user_id = %s AND user_type = 'patient'
            ORDER BY created_at DESC
        ''', (session['id'],))
        notifications = cursor.fetchall()
        
        return render_template('patient_notifications.html', notifications=notifications)
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'danger')
        return redirect(url_for('patient_dashboard'))
    finally:
        cursor.close()

@app.route('/patient/video-call')
def patient_video_call():
    if 'loggedin' not in session or session['user_type'] != 'patient':
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT vc.*, d.name as doctor_name 
        FROM video_calls vc 
        JOIN doctors d ON vc.doctor_id = d.id 
        WHERE vc.patient_id = %s 
        ORDER BY vc.scheduled_time DESC
    ''', (session['id'],))
    calls = cursor.fetchall()
    
    cursor.execute('SELECT id, name FROM doctors ORDER BY name')
    doctors = cursor.fetchall()
    
    return render_template('patient_video_call.html', 
                         calls=calls,
                         doctors=doctors)
@app.route('/patient/select-doctor')
def patient_select_doctor():
    # Your view logic here
    return render_template('select_doctor.html')

@app.route('/patient/schedule-call', methods=['POST'])
def patient_schedule_call():
    if 'loggedin' not in session or session.get('user_type') != 'patient':
        flash('Please login as a patient first!', 'danger')
        return redirect(url_for('login'))
    
    doctor_id = request.form.get('doctor_id')
    scheduled_time = request.form.get('scheduled_time')
    reason = request.form.get('reason')
    
    if not all([doctor_id, scheduled_time, reason]):
        flash('Please fill all required fields!', 'danger')
        return redirect(url_for('patient_video_call'))
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Check if doctor is available at that time
        cursor.execute('''
            SELECT id FROM video_calls 
            WHERE doctor_id = %s AND scheduled_time = %s
        ''', (doctor_id, scheduled_time))
        
        if cursor.fetchone():
            flash('Doctor is not available at this time. Please choose another time.', 'danger')
        else:
            cursor.execute('''
                INSERT INTO video_calls 
                (patient_id, doctor_id, scheduled_time, reason, status) 
                VALUES (%s, %s, %s, %s, 'Scheduled')
            ''', (session['id'], doctor_id, scheduled_time, reason))
            
            # Create notification for doctor
            cursor.execute('SELECT name FROM patients WHERE id = %s', (session['id'],))
            patient_name = cursor.fetchone()['name']
            
            notification_message = f'New video call scheduled by {patient_name} at {scheduled_time}'
            cursor.execute('''
                INSERT INTO notifications 
                (user_id, user_type, message, created_at) 
                VALUES (%s, 'doctor', %s, NOW())
            ''', (doctor_id, notification_message))
            
            mysql.connection.commit()
            flash('Video call scheduled successfully!', 'success')
    
    except Exception as e:
        flash(f'Error scheduling video call: {str(e)}', 'danger')
    
    finally:
        cursor.close()
    
    return redirect(url_for('patient_video_call'))

@app.route('/admin/init-db')
def admin_init_db():
    # WARNING: This route should be protected with authentication & authorization in production!
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('SELECT id, name, specialization FROM doctors WHERE status = "active" ORDER BY name')


        mysql.connection.commit()

        # Insert sample doctors if none exist
        cursor.execute('SELECT COUNT(*) AS count FROM doctors')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
                INSERT INTO doctors (name, email, phone, password, degree, specialization, experience, bio) 
                VALUES 
                ('Dr. Smith', 'dr.smith@example.com', '1234567890', 'password123', 'MD', 'Cardiology', 10, 'Senior Cardiologist with 10 years of experience'),
                ('Dr. Johnson', 'dr.johnson@example.com', '2345678901', 'password123', 'MBBS, MD', 'Neurology', 8, 'Neurology specialist'),
                ('Dr. Williams', 'dr.williams@example.com', '3456789012', 'password123', 'MBBS, MS', 'Orthopedics', 12, 'Orthopedic surgeon')
            ''')

        # Insert sample patients if none exist
        cursor.execute('SELECT COUNT(*) AS count FROM patients')
        if cursor.fetchone()['count'] == 0:
            cursor.execute('''
                INSERT INTO patients (name, email, phone, password, dob, gender, address, blood_group) 
                VALUES 
                ('John Doe', 'john.doe@example.com', '4567890123', 'password123', '1980-05-15', 'Male', '123 Main St, City', 'A+'),
                ('Jane Smith', 'jane.smith@example.com', '5678901234', 'password123', '1985-08-20', 'Female', '456 Oak Ave, Town', 'B+'),
                ('Robert Johnson', 'robert.j@example.com', '6789012345', 'password123', '1975-03-10', 'Male', '789 Pine Rd, Village', 'O+')
            ''')

        mysql.connection.commit()
        flash('Database initialized with sample data!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error initializing database: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('index'))


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
