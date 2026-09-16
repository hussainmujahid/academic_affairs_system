# app/routes/admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.models import (
    User, Student, Teacher, Department, Course, Semester, 
    RegistrationWindow, CourseSection, SystemLog,
    Attendance, Registration, Major, StudyPlan, StudyPlanCourse,
    StudyPlanResearch, Classroom, Timetable
)
from datetime import datetime, date
from sqlalchemy import text
import csv
from io import StringIO

bp = Blueprint('admin', __name__, url_prefix='/admin')


# =============================================
# DASHBOARD
# =============================================
@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    stats = {
        'total_users': User.query.count(),
        'total_students': Student.query.count(),
        'total_teachers': Teacher.query.count(),
        'total_departments': Department.query.count(),
        'total_courses': Course.query.count(),
        'total_sections': CourseSection.query.count(),
        'total_registrations': Registration.query.filter_by(status='enrolled').count(),
        'total_majors': Major.query.count(),
        'total_classrooms': Classroom.query.count(),
        'total_study_plans': StudyPlan.query.count(),  # Add this line
        'total_timetables': Timetable.query.count(),   # Add this line
        'active_semester': Semester.query.filter_by(is_active=True).first(),
    }
    
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, recent_logs=recent_logs)

# =============================================
# USER MANAGEMENT
# =============================================
@bp.route('/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    # Eager load relationships
    users = User.query.options(
        db.joinedload(User.teacher_profile).joinedload(Teacher.department),
        db.joinedload(User.teacher_profile).joinedload(Teacher.major_obj),
        db.joinedload(User.student_profile).joinedload(Student.major_obj)
    ).order_by(User.user_id).all()
    
    return render_template('admin/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@login_required
def create_user():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    departments = Department.query.all()
    majors = Major.query.all()
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('admin.create_user'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('admin.create_user'))
        
        actual_role = role
        admin_type = request.form.get('admin_type')
        
        if role == 'admin':
            if admin_type == 'super_admin':
                actual_role = 'admin'
            elif admin_type == 'department_admin':
                actual_role = 'department_admin'
        
        user = User(
            username=username, email=email,
            first_name=first_name, last_name=last_name,
            role=actual_role, is_active=True,
            created_at=datetime.utcnow()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        if actual_role == 'student':
            student = Student(
                student_id=user.user_id,
                student_number=f"STU{datetime.now().year}{user.user_id:04d}",
                enrollment_year=datetime.now().year,
                major_id=request.form.get('major_id') if request.form.get('major_id') else None,
                date_of_birth=datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date() if request.form.get('date_of_birth') else None,
                phone_number=request.form.get('phone_number')
            )
            db.session.add(student)
            flash(f'Student {username} created!', 'success')
            
        elif actual_role == 'teacher':
            # Use major_id instead of major string field
            teacher = Teacher(
                teacher_id=user.user_id,
                employee_number=f"EMP{datetime.now().year}{user.user_id:04d}",
                department_id=request.form.get('teacher_dept_id') if request.form.get('teacher_dept_id') else None,
                title=request.form.get('title', 'Instructor'),
                major_id=request.form.get('teacher_major_id') if request.form.get('teacher_major_id') else None,  # Changed from 'major' to 'major_id'
                research_area=request.form.get('research_area'),
                certifications=request.form.get('certifications'),
                date_of_birth=datetime.strptime(request.form['teacher_dob'], '%Y-%m-%d').date() if request.form.get('teacher_dob') else None,
                hire_date=date.today(),
                office_location=request.form.get('office_location'),
                office_phone=request.form.get('office_phone'),
                education=request.form.get('education'),
                is_department_admin=False
            )
            db.session.add(teacher)
            flash(f'Teacher {username} created!', 'success')
            
        elif actual_role == 'department_admin':
            teacher = Teacher(
                teacher_id=user.user_id,
                employee_number=f"EMP{datetime.now().year}{user.user_id:04d}",
                department_id=request.form.get('department_id') if request.form.get('department_id') else None,
                title='Department Admin',
                hire_date=date.today(),
                is_department_admin=True
            )
            db.session.add(teacher)
            flash(f'Department Admin {username} created!', 'success')
            
        elif actual_role == 'admin':
            flash(f'Super Admin {username} created!', 'success')
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='CREATE_USER',
            entity_type='user',
            entity_id=user.user_id,
            details=f"Created user {username} with role {actual_role}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/create_user.html', departments=departments, majors=majors)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    user = User.query.get_or_404(user_id)
    majors = Major.query.all()
    departments = Department.query.all()
    
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.is_active = 'is_active' in request.form
        
        if request.form.get('password'):
            user.set_password(request.form['password'])
        
             
        # Update student/teacher specific fields
        if user.role == 'student':
            student = Student.query.get(user_id)
            if student:
                student.major_id = request.form.get('major_id') if request.form.get('major_id') else None
                if request.form.get('date_of_birth'):
                    student.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
                student.phone_number = request.form.get('phone_number')
        
        elif user.role in ['teacher', 'department_admin']:
            teacher = Teacher.query.get(user_id)
            if teacher:
                teacher.department_id = request.form.get('department_id') if request.form.get('department_id') else None
                teacher.title = request.form.get('title')
                teacher.major_id = request.form.get('teacher_major_id') if request.form.get('teacher_major_id') else None  # Changed
                teacher.research_area = request.form.get('research_area')
                teacher.certifications = request.form.get('certifications')
                teacher.office_location = request.form.get('office_location')
                teacher.office_phone = request.form.get('office_phone')
                teacher.education = request.form.get('education')
                if request.form.get('teacher_dob'):
                    teacher.date_of_birth = datetime.strptime(request.form['teacher_dob'], '%Y-%m-%d').date()
        
        db.session.commit()
        flash(f'User {user.username} updated!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user=user, majors=majors, departments=departments)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.user_id == current_user.user_id:
        flash('You cannot delete yourself!', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    username = user.username
    
    try:
        # Handle based on role
        if user.role == 'student':
            student = Student.query.get(user_id)
            if student:
                # Delete registrations and related records
                for reg in student.registrations:
                    # Delete attendance records
                    Attendance.query.filter_by(registration_id=reg.registration_id).delete()
                    # Delete course evaluations
                    CourseEvaluation.query.filter_by(registration_id=reg.registration_id).delete()
                    # Delete grade audits
                    GradeAudit.query.filter_by(registration_id=reg.registration_id).delete()
                # Delete registrations
                Registration.query.filter_by(student_id=user_id).delete()
                # Delete waitlist entries
                Waitlist.query.filter_by(student_id=user_id).delete()
                # Delete study plans and related
                for plan in student.study_plans:
                    StudyPlanCourse.query.filter_by(plan_id=plan.plan_id).delete()
                    StudyPlanResearch.query.filter_by(plan_id=plan.plan_id).delete()
                StudyPlan.query.filter_by(student_id=user_id).delete()
                # Delete the student record
                db.session.delete(student)
        
        elif user.role in ['teacher', 'department_admin']:
            teacher = Teacher.query.get(user_id)
            if teacher:
                # Check if teacher has sections
                sections = CourseSection.query.filter_by(teacher_id=user_id).count()
                if sections > 0:
                    flash(f'Cannot delete: Teacher is assigned to {sections} section(s). Reassign sections first.', 'danger')
                    return redirect(url_for('admin.manage_users'))
                
                # Update research supervision
                StudyPlanResearch.query.filter_by(supervisor_id=user_id).update({'supervisor_id': None})
                # Update attendance marking
                Attendance.query.filter_by(marked_by=user_id).update({'marked_by': None})
                # Delete the teacher record
                db.session.delete(teacher)
        
        # Delete user logs (optional)
        SystemLog.query.filter_by(user_id=user_id).delete()
        
        # Finally delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'User {username} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_users'))

# =============================================
# MAJOR MANAGEMENT (New)
# =============================================
@bp.route('/majors')
@login_required
def manage_majors():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    majors = Major.query.all()
    departments = Department.query.all()
    return render_template('admin/majors.html', majors=majors, departments=departments)


@bp.route('/majors/create', methods=['POST'])
@login_required
def create_major():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    major_code = request.form['major_code'].upper().strip()
    major_name = request.form['major_name'].strip()
    
    # Check if major_code already exists
    existing = Major.query.filter_by(major_code=major_code).first()
    if existing:
        flash(f'Major code "{major_code}" already exists! Please use a different code.', 'danger')
        return redirect(url_for('admin.manage_majors'))
    
    major = Major(
        major_code=major_code,
        major_name=major_name,
        department_id=request.form.get('department_id') if request.form.get('department_id') else None,
        description=request.form.get('description'),
        required_credits=int(request.form.get('required_credits', 120)),
        is_active='is_active' in request.form
    )
    
    try:
        db.session.add(major)
        db.session.commit()
        flash(f'Major {major.major_name} created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating major: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_majors'))


@bp.route('/majors/<int:major_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_major(major_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    major = Major.query.get_or_404(major_id)
    departments = Department.query.all()
    
    if request.method == 'POST':
        major_code = request.form['major_code'].upper().strip()
        major_name = request.form['major_name'].strip()
        department_id = request.form.get('department_id') if request.form.get('department_id') else None
        description = request.form.get('description')
        required_credits = int(request.form.get('required_credits', 120))
        is_active = 'is_active' in request.form
        
        # Check if major_code already exists (excluding this major)
        existing = Major.query.filter(
            Major.major_code == major_code,
            Major.major_id != major_id
        ).first()
        
        if existing:
            flash(f'Major code "{major_code}" already exists! Please use a different code.', 'danger')
            return render_template('admin/edit_major.html', major=major, departments=departments)
        
        major.major_code = major_code
        major.major_name = major_name
        major.department_id = department_id
        major.description = description
        major.required_credits = required_credits
        major.is_active = is_active
        
        try:
            db.session.commit()
            flash(f'Major {major.major_name} updated!', 'success')
            return redirect(url_for('admin.manage_majors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating major: {str(e)}', 'danger')
    
    return render_template('admin/edit_major.html', major=major, departments=departments)

@bp.route('/majors/<int:major_id>/delete', methods=['POST'])
@login_required
def delete_major(major_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    major = Major.query.get_or_404(major_id)
    
    # Check if students are enrolled in this major
    students = Student.query.filter_by(major_id=major_id).count()
    if students > 0:
        flash(f'Cannot delete major "{major.major_name}" because {students} student(s) are enrolled.', 'danger')
        return redirect(url_for('admin.manage_majors'))
    
    major_name = major.major_name
    db.session.delete(major)
    db.session.commit()
    flash(f'Major "{major_name}" deleted!', 'success')
    return redirect(url_for('admin.manage_majors'))


# =============================================
# STUDY PLAN MANAGEMENT (New)
# =============================================
@bp.route('/study-plans')
@login_required
def manage_study_plans():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    study_plans = StudyPlan.query.all()
    students = Student.query.all()
    majors = Major.query.all()
    semesters = Semester.query.all()
    courses = Course.query.all()
    
    # Add current datetime for the template
    from datetime import datetime
    now = datetime.now()
    
    return render_template('admin/study_plans.html', 
                         study_plans=study_plans, 
                         students=students, 
                         majors=majors, 
                         semesters=semesters,
                         courses=courses,
                         now=now)


@bp.route('/study-plans/create', methods=['POST'])
@login_required
def create_study_plan():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    plan = StudyPlan(
        student_id=request.form['student_id'],
        major_id=request.form['major_id'],
        semester_id=request.form.get('semester_id') if request.form.get('semester_id') else None,
        plan_name=request.form['plan_name'],
        academic_year=int(request.form['academic_year']),
        semester_number=int(request.form.get('semester_number', 1)),
        status=request.form.get('status', 'active')
    )
    db.session.add(plan)
    db.session.commit()
    
    flash(f'Study plan "{plan.plan_name}" created!', 'success')
    return redirect(url_for('admin.manage_study_plans'))


@bp.route('/study-plans/<int:plan_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_study_plan(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    plan = StudyPlan.query.get_or_404(plan_id)
    students = Student.query.all()
    majors = Major.query.all()
    semesters = Semester.query.all()
    courses = Course.query.all()
    
    # Add current datetime for the template
    from datetime import datetime
    now = datetime.now()
    
    if request.method == 'POST':
        plan.student_id = request.form['student_id']
        plan.major_id = request.form['major_id']
        plan.semester_id = request.form.get('semester_id') if request.form.get('semester_id') else None
        plan.plan_name = request.form['plan_name']
        plan.academic_year = int(request.form['academic_year'])
        plan.semester_number = int(request.form.get('semester_number', 1))
        plan.status = request.form.get('status', 'active')
        db.session.commit()
        flash(f'Study plan "{plan.plan_name}" updated!', 'success')
        return redirect(url_for('admin.manage_study_plans'))
    
    return render_template('admin/edit_study_plan.html', 
                         plan=plan, 
                         students=students, 
                         majors=majors, 
                         semesters=semesters,
                         courses=courses,
                         now=now)


@bp.route('/study-plans/<int:plan_id>/add-course', methods=['POST'])
@login_required
def add_course_to_study_plan(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    # Check if course already exists in this study plan
    existing = StudyPlanCourse.query.filter_by(
        plan_id=plan_id,
        course_id=request.form['course_id']
    ).first()
    
    if existing:
        flash('This course is already in the study plan!', 'warning')
        return redirect(url_for('admin.edit_study_plan', plan_id=plan_id))
    
    plan_course = StudyPlanCourse(
        plan_id=plan_id,
        course_id=request.form['course_id'],
        is_required='is_required' in request.form,
        semester_offered=int(request.form.get('semester_offered', 0)),
        status='planned'
    )
    db.session.add(plan_course)
    db.session.commit()
    
    flash('Course added to study plan!', 'success')
    return redirect(url_for('admin.edit_study_plan', plan_id=plan_id))


@bp.route('/study-plans/<int:plan_id>/remove-course/<int:plan_course_id>', methods=['POST'])
@login_required
def remove_course_from_study_plan(plan_id, plan_course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    plan_course = StudyPlanCourse.query.get_or_404(plan_course_id)
    db.session.delete(plan_course)
    db.session.commit()
    
    flash('Course removed from study plan!', 'success')
    return redirect(url_for('admin.edit_study_plan', plan_id=plan_id))


@bp.route('/study-plans/<int:plan_id>/delete', methods=['POST'])
@login_required
def delete_study_plan(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    plan = StudyPlan.query.get_or_404(plan_id)
    plan_name = plan.plan_name
    db.session.delete(plan)
    db.session.commit()
    flash(f'Study plan "{plan_name}" deleted!', 'success')
    return redirect(url_for('admin.manage_study_plans'))

# =============================================
# STUDY PLAN RESEARCH MANAGEMENT (New)
# =============================================
@bp.route('/study-plans/<int:plan_id>/research')
@login_required
def manage_plan_research(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    plan = StudyPlan.query.get_or_404(plan_id)
    teachers = Teacher.query.all()
    
    return render_template('admin/plan_research.html', plan=plan, teachers=teachers)


@bp.route('/study-plans/<int:plan_id>/research/create', methods=['POST'])
@login_required
def create_research(plan_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    research = StudyPlanResearch(
        plan_id=plan_id,
        title=request.form['title'],
        description=request.form.get('description'),
        research_type=request.form.get('research_type'),
        supervisor_id=request.form.get('supervisor_id') if request.form.get('supervisor_id') else None,
        start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date() if request.form.get('start_date') else None,
        end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form.get('end_date') else None,
        status=request.form.get('status', 'proposed')
    )
    db.session.add(research)
    db.session.commit()
    
    flash(f'Research "{research.title}" created!', 'success')
    return redirect(url_for('admin.manage_plan_research', plan_id=plan_id))


@bp.route('/research/<int:research_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_research(research_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    research = StudyPlanResearch.query.get_or_404(research_id)
    teachers = Teacher.query.all()
    
    if request.method == 'POST':
        research.title = request.form['title']
        research.description = request.form.get('description')
        research.research_type = request.form.get('research_type')
        research.supervisor_id = request.form.get('supervisor_id') if request.form.get('supervisor_id') else None
        if request.form.get('start_date'):
            research.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        if request.form.get('end_date'):
            research.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        research.status = request.form.get('status', 'proposed')
        if request.form.get('grade'):
            research.grade = float(request.form['grade'])
        if request.form.get('submission_date'):
            research.submission_date = datetime.strptime(request.form['submission_date'], '%Y-%m-%d').date()
        db.session.commit()
        flash(f'Research "{research.title}" updated!', 'success')
        return redirect(url_for('admin.manage_plan_research', plan_id=research.plan_id))
    
    return render_template('admin/edit_research.html', research=research, teachers=teachers)


@bp.route('/research/<int:research_id>/delete', methods=['POST'])
@login_required
def delete_research(research_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    research = StudyPlanResearch.query.get_or_404(research_id)
    title = research.title
    db.session.delete(research)
    db.session.commit()
    flash(f'Research "{title}" deleted!', 'success')
    return redirect(url_for('admin.manage_study_plans'))


# =============================================
# CLASSROOM MANAGEMENT (New)
# =============================================
@bp.route('/classrooms')
@login_required
def manage_classrooms():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    classrooms = Classroom.query.all()
    return render_template('admin/classrooms.html', classrooms=classrooms)


@bp.route('/classrooms/create', methods=['POST'])
@login_required
def create_classroom():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    classroom = Classroom(
        room_number=request.form['room_number'],
        building=request.form.get('building'),
        capacity=int(request.form.get('capacity', 30)),
        room_type=request.form.get('room_type'),
        has_projector='has_projector' in request.form,
        has_computers='has_computers' in request.form,
        is_active=True
    )
    db.session.add(classroom)
    db.session.commit()
    flash(f'Classroom {classroom.room_number} created!', 'success')
    return redirect(url_for('admin.manage_classrooms'))


@bp.route('/classrooms/<int:classroom_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    if request.method == 'POST':
        classroom.room_number = request.form['room_number']
        classroom.building = request.form.get('building')
        classroom.capacity = int(request.form.get('capacity', 30))
        classroom.room_type = request.form.get('room_type')
        classroom.has_projector = 'has_projector' in request.form
        classroom.has_computers = 'has_computers' in request.form
        classroom.is_active = 'is_active' in request.form
        db.session.commit()
        flash(f'Classroom {classroom.room_number} updated!', 'success')
        return redirect(url_for('admin.manage_classrooms'))
    
    return render_template('admin/edit_classroom.html', classroom=classroom)


@bp.route('/classrooms/<int:classroom_id>/delete', methods=['POST'])
@login_required
def delete_classroom(classroom_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Check if classroom has timetables
    timetables = Timetable.query.filter_by(classroom_id=classroom_id).count()
    if timetables > 0:
        flash(f'Cannot delete classroom "{classroom.room_number}" because it has {timetables} timetable entry(s).', 'danger')
        return redirect(url_for('admin.manage_classrooms'))
    
    room_number = classroom.room_number
    db.session.delete(classroom)
    db.session.commit()
    flash(f'Classroom "{room_number}" deleted!', 'success')
    return redirect(url_for('admin.manage_classrooms'))


# =============================================
# TIMETABLE MANAGEMENT (New)
# =============================================
@bp.route('/timetables')
@login_required
def manage_timetables():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    timetables = Timetable.query.all()
    sections = CourseSection.query.all()
    classrooms = Classroom.query.all()
    
    return render_template('admin/timetables.html', 
                         timetables=timetables, 
                         sections=sections, 
                         classrooms=classrooms)


@bp.route('/timetables/create', methods=['POST'])
@login_required
def create_timetable():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    try:
        timetable = Timetable(
            section_id=request.form['section_id'],
            classroom_id=request.form['classroom_id'],
            day_of_week=int(request.form['day_of_week']),
            start_time=datetime.strptime(request.form['start_time'], '%H:%M').time(),
            end_time=datetime.strptime(request.form['end_time'], '%H:%M').time(),
            week_pattern=request.form.get('week_pattern', 'weekly'),
            is_active=True
        )
        db.session.add(timetable)
        db.session.commit()
        flash('Timetable entry created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_timetables'))


@bp.route('/timetables/<int:timetable_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_timetable(timetable_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    sections = CourseSection.query.all()
    classrooms = Classroom.query.all()
    
    if request.method == 'POST':
        try:
            timetable.section_id = request.form['section_id']
            timetable.classroom_id = request.form['classroom_id']
            timetable.day_of_week = int(request.form['day_of_week'])
            timetable.start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
            timetable.end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
            timetable.week_pattern = request.form.get('week_pattern', 'weekly')
            timetable.is_active = 'is_active' in request.form
            db.session.commit()
            flash('Timetable entry updated!', 'success')
            return redirect(url_for('admin.manage_timetables'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('admin/edit_timetable.html', 
                         timetable=timetable, 
                         sections=sections, 
                         classrooms=classrooms)


@bp.route('/timetables/<int:timetable_id>/delete', methods=['POST'])
@login_required
def delete_timetable(timetable_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    db.session.delete(timetable)
    db.session.commit()
    flash('Timetable entry deleted!', 'success')
    return redirect(url_for('admin.manage_timetables'))


# =============================================
# SECTION TIMETABLE VIEW (New)
# =============================================
@bp.route('/sections/<int:section_id>/timetable')
@login_required
def section_timetable(section_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    section = CourseSection.query.get_or_404(section_id)
    timetables = Timetable.query.filter_by(section_id=section_id).all()
    
    return render_template('admin/section_timetable.html', section=section, timetables=timetables)


# =============================================
# DEPARTMENTAL ADMIN
# =============================================
@bp.route('/users/make-department-admin/<int:user_id>', methods=['POST'])
@login_required
def make_department_admin(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.role != 'teacher':
        flash('Only teachers can be department admins', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user.role = 'department_admin'
    
    teacher = Teacher.query.get(user_id)
    if teacher:
        teacher.is_department_admin = True
    
    db.session.commit()
    flash(f'{user.username} is now a Department Admin!', 'success')
    return redirect(url_for('admin.manage_users'))


@bp.route('/users/remove-department-admin/<int:user_id>', methods=['POST'])
@login_required
def remove_department_admin(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.role != 'department_admin':
        flash('User is not a department admin', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user.role = 'teacher'
    
    teacher = Teacher.query.get(user_id)
    if teacher:
        teacher.is_department_admin = False
    
    db.session.commit()
    flash(f'{user.username} is no longer a Department Admin', 'success')
    return redirect(url_for('admin.manage_users'))


# =============================================
# DEPARTMENT MANAGEMENT
# =============================================
@bp.route('/departments')
@login_required
def manage_departments():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    departments = Department.query.all()
    teachers = Teacher.query.all()
    return render_template('admin/departments.html', departments=departments, teachers=teachers)


@bp.route('/departments/create', methods=['POST'])
@login_required
def create_department():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    dept = Department(
        department_code=request.form['department_code'],
        department_name=request.form['department_name'],
        dean_id=request.form.get('dean_id') if request.form.get('dean_id') else None
    )
    db.session.add(dept)
    db.session.commit()
    flash(f'Department {dept.department_name} created!', 'success')
    return redirect(url_for('admin.manage_departments'))


@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_department(dept_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    dept = Department.query.get_or_404(dept_id)
    teachers = Teacher.query.all()
    
    if request.method == 'POST':
        dept.department_code = request.form['department_code']
        dept.department_name = request.form['department_name']
        
        dean_id = request.form.get('dean_id')
        if dean_id and dean_id != '':
            dept.dean_id = int(dean_id)
        else:
            dept.dean_id = None
        
        db.session.commit()
        flash(f'Department {dept.department_name} updated!', 'success')
        return redirect(url_for('admin.manage_departments'))
    
    return render_template('admin/edit_department.html', dept=dept, teachers=teachers)


@bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
def delete_department(dept_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    dept = Department.query.get_or_404(dept_id)
    
    # Check if department has courses
    courses = Course.query.filter_by(department_id=dept_id).count()
    if courses > 0:
        flash(f'Cannot delete department "{dept.department_name}" because it has {courses} course(s).', 'danger')
        return redirect(url_for('admin.manage_departments'))
    
    # Check if department has teachers
    teachers = Teacher.query.filter_by(department_id=dept_id).count()
    if teachers > 0:
        flash(f'Cannot delete department "{dept.department_name}" because it has {teachers} teacher(s).', 'danger')
        return redirect(url_for('admin.manage_departments'))
    
    db.session.delete(dept)
    db.session.commit()
    flash(f'Department {dept.department_name} deleted!', 'success')
    return redirect(url_for('admin.manage_departments'))


# =============================================
# COURSE MANAGEMENT
# =============================================
@bp.route('/courses')
@login_required
def manage_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    courses = Course.query.all()
    departments = Department.query.all()
    return render_template('admin/courses.html', courses=courses, departments=departments)


@bp.route('/courses/create', methods=['POST'])
@login_required
def create_course():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    # Check if course code exists
    existing = Course.query.filter_by(course_code=request.form['course_code']).first()
    if existing:
        flash(f'Course code "{request.form["course_code"]}" already exists!', 'danger')
        return redirect(url_for('admin.manage_courses'))
    
    course = Course(
        course_code=request.form['course_code'],
        title=request.form['title'],
        credits=int(request.form['credits']),
        department_id=request.form.get('department_id') if request.form.get('department_id') else None,
        description=request.form.get('description')
    )
    db.session.add(course)
    db.session.commit()
    flash(f'Course {course.course_code} created!', 'success')
    return redirect(url_for('admin.manage_courses'))


@bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    course = Course.query.get_or_404(course_id)
    departments = Department.query.all()
    
    if request.method == 'POST':
        # Check if course code exists (excluding this course)
        existing = Course.query.filter(
            Course.course_code == request.form['course_code'],
            Course.course_id != course_id
        ).first()
        
        if existing:
            flash(f'Course code "{request.form["course_code"]}" already exists!', 'danger')
            return redirect(url_for('admin.edit_course', course_id=course_id))
        
        course.course_code = request.form['course_code']
        course.title = request.form['title']
        course.credits = int(request.form['credits'])
        course.department_id = request.form.get('department_id') if request.form.get('department_id') else None
        course.description = request.form.get('description')
        db.session.commit()
        flash(f'Course {course.course_code} updated!', 'success')
        return redirect(url_for('admin.manage_courses'))
    
    return render_template('admin/edit_course.html', course=course, departments=departments)


@bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    course = Course.query.get_or_404(course_id)
    
    # Check if course has sections
    sections = CourseSection.query.filter_by(course_id=course_id).count()
    
    if sections > 0:
        flash(f'Cannot delete course "{course.course_code}" because it has {sections} section(s). Delete the sections first.', 'danger')
        return redirect(url_for('admin.manage_courses'))
    
    course_code = course.course_code
    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course_code}" deleted successfully!', 'success')
    return redirect(url_for('admin.manage_courses'))


# =============================================
# SEMESTER MANAGEMENT
# =============================================
@bp.route('/semesters')
@login_required
def manage_semesters():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    semesters = Semester.query.order_by(Semester.year.desc()).all()
    from datetime import datetime
    return render_template('admin/semesters.html', semesters=semesters, now=datetime.now())


@bp.route('/semesters/create', methods=['POST'])
@login_required
def create_semester():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    try:
        semester = Semester(
            semester_code=request.form['semester_code'],
            semester_name=request.form['semester_name'],
            year=int(request.form['year']),
            start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
            is_active='is_active' in request.form
        )
        db.session.add(semester)
        db.session.commit()
        flash(f'Semester {semester.semester_name} created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_semesters'))


@bp.route('/semesters/<int:semester_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_semester(semester_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    semester = Semester.query.get_or_404(semester_id)
    
    if request.method == 'POST':
        semester.semester_code = request.form['semester_code']
        semester.semester_name = request.form['semester_name']
        semester.year = int(request.form['year'])
        semester.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        semester.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        semester.is_active = 'is_active' in request.form
        db.session.commit()
        flash(f'Semester {semester.semester_name} updated!', 'success')
        return redirect(url_for('admin.manage_semesters'))
    
    return render_template('admin/edit_semester.html', semester=semester)


@bp.route('/semesters/<int:semester_id>/delete', methods=['POST'])
@login_required
def delete_semester(semester_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    semester = Semester.query.get_or_404(semester_id)
    
    # Check if semester has sections
    sections = CourseSection.query.filter_by(semester_id=semester_id).count()
    if sections > 0:
        flash(f'Cannot delete semester "{semester.semester_name}" because it has {sections} section(s).', 'danger')
        return redirect(url_for('admin.manage_semesters'))
    
    db.session.delete(semester)
    db.session.commit()
    flash(f'Semester {semester.semester_name} deleted!', 'success')
    return redirect(url_for('admin.manage_semesters'))


@bp.route('/semesters/<int:semester_id>/activate', methods=['POST'])
@login_required
def activate_semester(semester_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    Semester.query.update({'is_active': False})
    semester = Semester.query.get_or_404(semester_id)
    semester.is_active = True
    db.session.commit()
    flash(f'{semester.semester_name} is now active!', 'success')
    return redirect(url_for('admin.manage_semesters'))


# =============================================
# SECTION MANAGEMENT
# =============================================
@bp.route('/sections')
@login_required
def manage_sections():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    sections = CourseSection.query.options(
        db.joinedload(CourseSection.course),
        db.joinedload(CourseSection.semester),
        db.joinedload(CourseSection.teacher).joinedload(Teacher.user)
    ).all()
    
    courses = Course.query.all()
    teachers = Teacher.query.options(db.joinedload(Teacher.user)).all()
    semesters = Semester.query.all()
    
    return render_template('admin/sections.html', 
                         sections=sections, 
                         courses=courses, 
                         teachers=teachers, 
                         semesters=semesters)


@bp.route('/sections/create', methods=['POST'])
@login_required
def create_section():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    try:
        course_id = request.form.get('course_id')
        semester_id = request.form.get('semester_id')
        section_number = request.form.get('section_number')
        teacher_id = request.form.get('teacher_id')
        capacity = request.form.get('capacity')
        
        if teacher_id and teacher_id != '':
            teacher_id_int = int(teacher_id)
        else:
            teacher_id_int = None
        
        section = CourseSection(
            course_id=int(course_id),
            semester_id=int(semester_id),
            section_number=section_number,
            teacher_id=teacher_id_int,
            capacity=int(capacity),
            status='open'
        )
        db.session.add(section)
        db.session.commit()
        
        flash(f'Section {section.section_number} created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating section: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_sections'))


@bp.route('/sections/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_section(section_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    section = CourseSection.query.options(
        db.joinedload(CourseSection.teacher).joinedload(Teacher.user)
    ).get_or_404(section_id)
    
    courses = Course.query.all()
    teachers = Teacher.query.options(db.joinedload(Teacher.user)).all()
    semesters = Semester.query.all()
    
    if request.method == 'POST':
        try:
            teacher_id = request.form.get('teacher_id')
            
            if teacher_id and teacher_id != '':
                teacher_id_int = int(teacher_id)
            else:
                teacher_id_int = None
            
            section.course_id = int(request.form['course_id'])
            section.semester_id = int(request.form['semester_id'])
            section.section_number = request.form['section_number']
            section.teacher_id = teacher_id_int
            section.capacity = int(request.form['capacity'])
            section.status = request.form.get('status', 'open')
            
            db.session.commit()
            flash(f'Section {section.section_number} updated!', 'success')
            return redirect(url_for('admin.manage_sections'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating section: {str(e)}', 'danger')
    
    return render_template('admin/edit_section.html', 
                         section=section, 
                         courses=courses, 
                         teachers=teachers, 
                         semesters=semesters)


@bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    registration_count = Registration.query.filter_by(section_id=section_id).count()
    
    if registration_count > 0:
        flash(f'Cannot delete section: {registration_count} student(s) are registered.', 'danger')
        return redirect(url_for('admin.manage_sections'))
    
    # Also check for timetables
    timetable_count = Timetable.query.filter_by(section_id=section_id).count()
    if timetable_count > 0:
        flash(f'Cannot delete section: It has {timetable_count} timetable entry(s). Delete timetables first.', 'danger')
        return redirect(url_for('admin.manage_sections'))
    
    section_name = f"{section.course.course_code if section.course else 'Unknown'} - Section {section.section_number}"
    db.session.delete(section)
    db.session.commit()
    flash(f'Section {section_name} deleted!', 'success')
    return redirect(url_for('admin.manage_sections'))


@bp.route('/sections/<int:section_id>/cancel', methods=['POST'])
@login_required
def cancel_section(section_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    if section.status == 'cancelled':
        flash('Section is already cancelled!', 'warning')
        return redirect(url_for('admin.manage_sections'))
    
    section.status = 'cancelled'
    db.session.commit()
    
    flash(f'Section {section.section_number} for {section.course.course_code} has been cancelled!', 'success')
    return redirect(url_for('admin.manage_sections'))


# =============================================
# REGISTRATION WINDOWS MANAGEMENT
# =============================================
@bp.route('/registration-windows')
@login_required
def manage_registration_windows():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    windows = RegistrationWindow.query.all()
    semesters = Semester.query.all()
    return render_template('admin/registration_windows.html', windows=windows, semesters=semesters, datetime=datetime)


@bp.route('/registration-windows/create', methods=['POST'])
@login_required
def create_registration_window():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    try:
        window = RegistrationWindow(
            semester_id=request.form['semester_id'],
            window_name=request.form['window_name'],
            start_datetime=datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M'),
            end_datetime=datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M'),
            priority=int(request.form.get('priority', 0))
        )
        db.session.add(window)
        db.session.commit()
        flash(f'Registration window "{window.window_name}" created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('admin.manage_registration_windows'))


@bp.route('/registration-windows/<int:window_id>/delete', methods=['POST'])
@login_required
def delete_registration_window(window_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    window = RegistrationWindow.query.get_or_404(window_id)
    db.session.delete(window)
    db.session.commit()
    flash('Registration window deleted!', 'success')
    return redirect(url_for('admin.manage_registration_windows'))


@bp.route('/registration-windows/<int:window_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_registration_window(window_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    window = RegistrationWindow.query.get_or_404(window_id)
    semesters = Semester.query.all()
    
    if request.method == 'POST':
        window.semester_id = request.form['semester_id']
        window.window_name = request.form['window_name']
        window.start_datetime = datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M')
        window.end_datetime = datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M')
        window.priority = int(request.form.get('priority', 0))
        
        db.session.commit()
        flash('Registration window updated!', 'success')
        return redirect(url_for('admin.manage_registration_windows'))
    
    return render_template('admin/edit_registration_window.html', 
                         window=window, 
                         semesters=semesters,
                         datetime=datetime)


# =============================================
# SYSTEM LOGS
# =============================================
@bp.route('/logs')
@login_required
def view_logs():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    logs = SystemLog.query.order_by(SystemLog.created_at.desc()).paginate(per_page=50)
    return render_template('admin/logs.html', logs=logs)


# =============================================
# REPORTS
# =============================================
@bp.route('/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    enrollment_stats = db.session.execute(text("""
        SELECT c.course_code, c.title, cs.section_number,
               cs.capacity, cs.enrolled_count,
               ROUND(100.0 * cs.enrolled_count / NULLIF(cs.capacity, 0), 2) as utilization,
               s.semester_name
        FROM course_sections cs
        JOIN courses c ON cs.course_id = c.course_id
        JOIN semesters s ON cs.semester_id = s.semester_id
        WHERE s.is_active = true
        ORDER BY utilization DESC
    """)).fetchall()
    
    # Get departments and student counts for the chart
    departments = Department.query.all()
    
    # Build a dictionary with department names and student counts (not Student objects)
    students_by_dept = {}
    for dept in departments:
        # Count students in this department using the Major relationship
        count = Student.query.join(Major).filter(Major.department_id == dept.department_id).count()
        if count > 0:
            students_by_dept[dept.department_name] = count
    
    # Also get students with no major
    students_no_major = Student.query.filter(Student.major_id.is_(None)).count()
    if students_no_major > 0:
        students_by_dept['No Major'] = students_no_major
    
    return render_template('admin/reports.html', 
                         enrollment_stats=enrollment_stats,
                         departments=departments,
                         students_by_dept=students_by_dept)


@bp.route('/reports/export')
@login_required
def export_enrollment_report():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    enrollment_stats = db.session.execute(text("""
        SELECT c.course_code, c.title, cs.section_number,
               cs.capacity, cs.enrolled_count,
               ROUND(100.0 * cs.enrolled_count / NULLIF(cs.capacity, 0), 2) as utilization,
               s.semester_name
        FROM course_sections cs
        JOIN courses c ON cs.course_id = c.course_id
        JOIN semesters s ON cs.semester_id = s.semester_id
        WHERE s.is_active = true
        ORDER BY utilization DESC
    """)).fetchall()
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Course Code', 'Course Title', 'Section', 'Semester', 
                     'Capacity', 'Enrolled', 'Available Seats', 'Utilization %'])
    
    for stat in enrollment_stats:
        writer.writerow([
            stat.course_code,
            stat.title,
            stat.section_number,
            stat.semester_name,
            stat.capacity,
            stat.enrolled_count,
            stat.capacity - stat.enrolled_count,
            f"{stat.utilization}%"
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=enrollment_report.csv'}
    )


# =============================================
# STUDENTS BY DEPARTMENT
# =============================================
@bp.route('/students-by-department')
@login_required
def students_by_department():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    departments = Department.query.all()
    
    students_by_dept = {}
    for dept in departments:
        students = Student.query.join(Major).filter(Major.department_id == dept.department_id).all()
        students_by_dept[dept.department_name] = students
    
    students_no_major = Student.query.filter(Student.major_id.is_(None)).all()
    
    return render_template('admin/students_by_dept.html', 
                         students_by_dept=students_by_dept,
                         students_no_major=students_no_major,
                         departments=departments)


# =============================================
# TEACHERS BY DEPARTMENT
# =============================================
@bp.route('/teachers-by-department')
@login_required
def teachers_by_department():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    departments = Department.query.all()
    
    teachers_by_dept = {}
    for dept in departments:
        teachers = Teacher.query.filter_by(department_id=dept.department_id).all()
        teachers_by_dept[dept.department_name] = teachers
    
    teachers_no_dept = Teacher.query.filter(Teacher.department_id.is_(None)).all()
    
    return render_template('admin/teachers_by_dept.html', 
                         teachers_by_dept=teachers_by_dept,
                         teachers_no_dept=teachers_no_dept,
                         departments=departments)


# =============================================
# SEARCH USERS API
# =============================================
@bp.route('/api/search-users')
@login_required
def search_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    query = request.args.get('q', '')
    role = request.args.get('role', '')
    department = request.args.get('department', '')
    
    users_query = User.query
    
    if query:
        users_query = users_query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        )
    
    if role:
        users_query = users_query.filter_by(role=role)
    
    users = users_query.limit(50).all()
    
    results = []
    for user in users:
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'created_at': user.created_at.strftime('%Y-%m-%d') if user.created_at else None
        }
        
        if user.role == 'teacher' and user.teacher:
            user_data['department'] = user.teacher.department.department_name if user.teacher.department else 'Not Assigned'
            user_data['title'] = user.teacher.title
        elif user.role == 'student' and user.student:
            user_data['major'] = user.student.major_obj.major_name if user.student.major_obj else 'Undeclared'
        
        results.append(user_data)
    
    return jsonify(results)