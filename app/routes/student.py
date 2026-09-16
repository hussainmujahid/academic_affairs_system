# app/routes/student.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Student, CourseSection, Registration, Attendance, Semester, Course, Timetable  
from datetime import datetime
from sqlalchemy import text
from app.models import RegistrationWindow
from datetime import datetime
from sqlalchemy import func

bp = Blueprint('student', __name__, url_prefix='/student')


@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    
    if not student:
        flash('Student profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Current registrations
    registrations = Registration.query.filter_by(
        student_id=student.student_id,
        status='enrolled'
    ).all()
    
    total_credits = sum(reg.section.course.credits for reg in registrations)
    
    # Completed grades
    completed_grades = Registration.query.filter_by(
        student_id=student.student_id,
        status='completed'
    ).all()
    
    return render_template('student/dashboard.html',
                         student=student,
                         registrations=registrations,
                         total_credits=total_credits,
                         completed_grades=completed_grades)


@bp.route('/courses')
@login_required
def available_courses():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    
    # Get active semester
    active_semester = Semester.query.filter_by(is_active=True).first()
    
    if not active_semester:
        flash('No active semester found. Please contact administrator.', 'warning')
        return render_template('student/courses.html', sections=[], active_window=None)
    
    # Get active registration window
    now = datetime.utcnow()
    active_window = RegistrationWindow.query.filter(
        RegistrationWindow.start_datetime <= now,
        RegistrationWindow.end_datetime >= now
    ).first()
    
    # Get registered section IDs
    registered_sections = [r.section_id for r in Registration.query.filter_by(
        student_id=student.student_id,
        status='enrolled'
    ).all()]
    
    # Get available sections
    sections = CourseSection.query.filter(
        CourseSection.semester_id == active_semester.semester_id,
        CourseSection.status == 'open',
        CourseSection.enrolled_count < CourseSection.capacity
    ).all()
    
    # Filter out already registered sections
    available_sections = [s for s in sections if s.section_id not in registered_sections]
    
    # Get completed courses for prerequisite checking
    completed_courses = db.session.execute(
        text("""
            SELECT c.course_id, c.course_code, c.title, r.grade
            FROM registrations r
            JOIN course_sections cs ON r.section_id = cs.section_id
            JOIN courses c ON cs.course_id = c.course_id
            WHERE r.student_id = :student_id 
            AND r.status = 'completed'
            AND r.grade >= 60
        """),
        {"student_id": student.student_id}
    ).fetchall()
    
    completed_course_ids = [c.course_id for c in completed_courses]
    
    return render_template('student/courses.html', 
                         sections=available_sections,
                         active_semester=active_semester,
                         active_window=active_window,
                         completed_courses=completed_courses,
                         completed_course_ids=completed_course_ids)


@bp.route('/register/<int:section_id>', methods=['POST'])
@login_required
def register_course(section_id):
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    if not student:
        flash('Student profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    # =============================================
    # 1. CHECK REGISTRATION WINDOW
    # =============================================
    now = datetime.utcnow()
    active_window = RegistrationWindow.query.filter(
        RegistrationWindow.start_datetime <= now,
        RegistrationWindow.end_datetime >= now
    ).first()
    
    if not active_window:
        flash('Registration is not open at this time. Please check the registration schedule.', 'danger')
        return redirect(url_for('student.available_courses'))
    
    # =============================================
    # 2. CHECK COURSE CAPACITY
    # =============================================
    if section.enrolled_count >= section.capacity:
        flash(f'Course is full! (Capacity: {section.capacity})', 'danger')
        return redirect(url_for('student.available_courses'))
    
    # =============================================
    # 3. CHECK SCHEDULE CONFLICT (Read-only check using existing timetables)
    # =============================================
    # Get timetables for the section the student wants to register for
    section_timetables = Timetable.query.filter_by(section_id=section_id, is_active=True).all()
    
    if section_timetables:
        # Get student's current enrolled sections
        current_registrations = Registration.query.filter_by(
            student_id=student.student_id,
            status='enrolled'
        ).all()
        
        # Check for conflicts with existing registrations
        for reg in current_registrations:
            existing_timetables = Timetable.query.filter_by(section_id=reg.section_id, is_active=True).all()
            
            for new_tt in section_timetables:
                for existing_tt in existing_timetables:
                    # Check if same day and time overlaps
                    if new_tt.day_of_week == existing_tt.day_of_week:
                        if (new_tt.start_time < existing_tt.end_time and 
                            new_tt.end_time > existing_tt.start_time):
                            conflict_course = reg.section.course
                            flash(f'Schedule conflict! This course conflicts with {conflict_course.course_code}.', 'danger')
                            return redirect(url_for('student.available_courses'))
    
    # =============================================
    # 4. CHECK IF ALREADY REGISTERED
    # =============================================
    existing = Registration.query.filter_by(
        student_id=student.student_id,
        section_id=section_id
    ).first()
    
    if existing:
        if existing.status == 'enrolled':
            flash('You are already registered for this course!', 'warning')
        elif existing.status == 'dropped':
            # Re-register - update the existing record
            existing.status = 'enrolled'
            existing.registration_date = datetime.utcnow()
            existing.drop_date = None
            existing.drop_reason = None
            section.enrolled_count += 1
            db.session.commit()
            flash(f'Successfully re-registered for {section.course.course_code}!', 'success')
        return redirect(url_for('student.dashboard'))
    
    # =============================================
    # 5. CREATE NEW REGISTRATION
    # =============================================
    registration = Registration(
        student_id=student.student_id,
        section_id=section_id,
        registration_date=datetime.utcnow(),
        status='enrolled'
    )
    db.session.add(registration)
    section.enrolled_count += 1
    
    try:
        db.session.commit()
        flash(f'Successfully registered for {section.course.course_code}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Registration failed: {str(e)}', 'danger')
    
    return redirect(url_for('student.dashboard'))



@bp.route('/withdraw/<int:registration_id>', methods=['POST'])
@login_required
def withdraw_course(registration_id):
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    registration = Registration.query.get_or_404(registration_id)
    
    if registration.student_id != current_user.user_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('student.dashboard'))
    
    registration.status = 'dropped'
    registration.drop_date = datetime.utcnow()
    registration.drop_reason = request.form.get('reason', 'Student withdrawal')
    
    # Decrease enrolled count
    section = registration.section
    section.enrolled_count -= 1
    
    db.session.commit()
    flash(f'Withdrawn from {section.course.course_code}', 'success')
    return redirect(url_for('student.dashboard'))


@bp.route('/schedule')
@login_required
def schedule():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    if not student:
        flash('Student profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Get all registrations for this student
    registrations = Registration.query.filter_by(
        student_id=student.student_id,
        status='enrolled'
    ).all()
    
    # Get all timetables for the sections the student is enrolled in
    section_ids = [reg.section_id for reg in registrations]
    timetables = Timetable.query.filter(
        Timetable.section_id.in_(section_ids),
        Timetable.is_active == True
    ).order_by(
        Timetable.day_of_week,
        Timetable.start_time
    ).all()
    
    return render_template('student/timetable.html', 
                         student=student, 
                         timetables=timetables)


@bp.route('/grades')
@login_required
def grades():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    
    if not student:
        flash('Student profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Get all registrations
    registrations = Registration.query.filter_by(student_id=student.student_id).all()
    
    # Calculate GPA and total credits
    total_grade_points = 0
    total_credits = 0
    completed_courses = 0
    in_progress_courses = 0
    
    for reg in registrations:
        if reg.status == 'completed' and reg.grade:
            credits = reg.section.course.credits
            if reg.grade >= 90:
                grade_points = 4.0
            elif reg.grade >= 80:
                grade_points = 3.0
            elif reg.grade >= 70:
                grade_points = 2.0
            elif reg.grade >= 60:
                grade_points = 1.0
            else:
                grade_points = 0.0
            total_grade_points += grade_points * credits
            total_credits += credits
            completed_courses += 1
        elif reg.status == 'enrolled':
            in_progress_courses += 1
    
    gpa = total_grade_points / total_credits if total_credits > 0 else 0
    
    return render_template('student/grades.html',
                         registrations=registrations,
                         gpa=gpa,
                         total_credits=total_credits,
                         completed_courses=completed_courses,
                         in_progress_courses=in_progress_courses)


@bp.route('/attendance')
@login_required
def attendance():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    
    # Get all registrations for this student
    registrations = Registration.query.filter_by(student_id=student.student_id).all()
    
    attendance_stats = []
    total_present = 0
    total_absent = 0
    total_late = 0
    
    for reg in registrations:
        attendances = Attendance.query.filter_by(registration_id=reg.registration_id).all()
        
        present = sum(1 for a in attendances if a.status == 'present')
        absent = sum(1 for a in attendances if a.status == 'absent')
        late = sum(1 for a in attendances if a.status == 'late')
        total = len(attendances)
        percentage = (present / total * 100) if total > 0 else 0
        
        total_present += present
        total_absent += absent
        total_late += late
        
        attendance_stats.append({
            'course_code': reg.section.course.course_code,
            'course_title': reg.section.course.title,
            'section_number': reg.section.section_number,
            'present': present,
            'absent': absent,
            'late': late,
            'total': total,
            'percentage': percentage
        })
    
    return render_template('student/attendance.html',
                         attendance_stats=attendance_stats,
                         total_present=total_present,
                         total_absent=total_absent,
                         total_late=total_late)

# =============================================
# STUDENT TIMETABLE VIEW
# =============================================
@bp.route('/timetable')
@login_required
def view_timetable():
    if current_user.role != 'student':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    student = Student.query.filter_by(student_id=current_user.user_id).first()
    if not student:
        flash('Student profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Get all registrations for this student
    registrations = Registration.query.filter_by(
        student_id=student.student_id,
        status='enrolled'
    ).all()
    
    # Get all timetables for the sections the student is enrolled in
    section_ids = [reg.section_id for reg in registrations]
    timetables = Timetable.query.filter(
        Timetable.section_id.in_(section_ids),
        Timetable.is_active == True
    ).order_by(
        Timetable.day_of_week,
        Timetable.start_time
    ).all()
    
    return render_template('student/timetable.html', 
                         student=student, 
                         timetables=timetables)