# app/routes/department_admin.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import (
    User, Student, Teacher, Department, Course, RegistrationWindow,
    CourseSection, Registration, Semester, SystemLog, Major,
    StudyPlan, StudyPlanCourse, StudyPlanResearch, Classroom, Timetable
)
from datetime import datetime, date
from sqlalchemy import text

bp = Blueprint('dept_admin', __name__, url_prefix='/dept-admin')


def get_admin_department():
    """Get the department of the current department admin"""
    print(f"DEBUG get_admin_department: user_id={current_user.user_id}, role={current_user.role}")
    
    # First, check if user is department_admin
    if current_user.role != 'department_admin':
        print(f"DEBUG: User {current_user.username} is not department_admin, role={current_user.role}")
        return None
    
    # Get teacher record
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher:
        print(f"DEBUG: No teacher record found for user_id {current_user.user_id}")
        # Try to create teacher record for this user
        teacher = Teacher(
            teacher_id=current_user.user_id,
            employee_number=f"EMP{datetime.now().year}{current_user.user_id:04d}",
            title='Department Administrator',
            hire_date=date.today(),
            is_department_admin=True
        )
        db.session.add(teacher)
        db.session.commit()
        print(f"DEBUG: Created teacher record for user {current_user.username}")
        return None
    
    print(f"DEBUG: Found teacher: id={teacher.teacher_id}, is_department_admin={teacher.is_department_admin}, department_id={teacher.department_id}")
    
    # Check if teacher is marked as department admin
    if not teacher.is_department_admin:
        print(f"DEBUG: Teacher {teacher.employee_number} is not marked as department_admin")
        # Auto-fix: Set as department admin
        teacher.is_department_admin = True
        db.session.commit()
        print(f"DEBUG: Auto-fixed - set is_department_admin=True for {teacher.employee_number}")
    
    # Get department
    if not teacher.department:
        print(f"DEBUG: Teacher {teacher.employee_number} has no department assigned")
        # Try to assign to first department as fallback
        first_dept = Department.query.first()
        if first_dept:
            teacher.department_id = first_dept.department_id
            db.session.commit()
            print(f"DEBUG: Auto-assigned teacher to department: {first_dept.department_name}")
            return first_dept
        return None
    
    print(f"DEBUG: Returning department: {teacher.department.department_name}")
    return teacher.department

def check_dept_access(item_department_id):
    """Check if item belongs to admin's department"""
    admin_dept = get_admin_department()
    if not admin_dept:
        return False
    return admin_dept.department_id == item_department_id


# =============================================
# DASHBOARD
# =============================================
@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Your account is not associated with any department. Please contact system administrator.', 'danger')
        return redirect(url_for('index.index'))
    
    # Get statistics - updated to use major_id instead of major string
    stats = {
        'total_students': Student.query.join(Major).filter(Major.department_id == admin_dept.department_id).count(),
        'total_teachers': Teacher.query.filter_by(department_id=admin_dept.department_id).count(),
        'total_courses': Course.query.filter_by(department_id=admin_dept.department_id).count(),
        'total_sections': CourseSection.query.join(Course).filter(
            Course.department_id == admin_dept.department_id
        ).count(),
        'total_classrooms': Classroom.query.count(),  # Classrooms are shared across departments
        'total_timetables': Timetable.query.join(
            CourseSection, Timetable.section_id == CourseSection.section_id
        ).join(
            Course, CourseSection.course_id == Course.course_id
        ).filter(
            Course.department_id == admin_dept.department_id
        ).count(),
        'total_registrations': Registration.query.join(
            CourseSection, Registration.section_id == CourseSection.section_id
        ).join(
            Course, CourseSection.course_id == Course.course_id
        ).filter(
            Course.department_id == admin_dept.department_id,
            Registration.status == 'enrolled'
        ).count(),
    }
    
    # Recent registrations
    recent_registrations = Registration.query.join(
        CourseSection, Registration.section_id == CourseSection.section_id
    ).join(
        Course, CourseSection.course_id == Course.course_id
    ).join(
        Student, Registration.student_id == Student.student_id
    ).join(
        User, Student.student_id == User.user_id
    ).filter(
        Course.department_id == admin_dept.department_id
    ).order_by(
        Registration.registration_date.desc()
    ).limit(10).all()
    
    return render_template('department_admin/dashboard.html', 
                         stats=stats, 
                         department=admin_dept,
                         recent_registrations=recent_registrations)


# =============================================
# STUDENT MANAGEMENT
# =============================================
@bp.route('/students')
@login_required
def manage_students():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    students = Student.query.join(Major).filter(Major.department_id == admin_dept.department_id).all()
    
    valid_students = []
    for s in students:
        if s.user:
            valid_students.append(s)
        else:
            regs = Registration.query.filter_by(student_id=s.student_id).count()
            if regs == 0:
                db.session.delete(s)
                print(f"Deleted orphaned student ID {s.student_id}")
            else:
                print(f"Cannot delete student ID {s.student_id} - has {regs} registrations")
    
    db.session.commit()
    
    return render_template('department_admin/students.html', 
                         students=valid_students, 
                         department=admin_dept)


@bp.route('/students/<int:student_id>/view')
@login_required
def view_student(student_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    
    if not student.major_obj or student.major_obj.department_id != admin_dept.department_id:
        flash('Student not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_students'))
    
    registrations = Registration.query.filter_by(student_id=student_id).all()
    
    return render_template('department_admin/student_details.html', 
                         student=student, 
                         registrations=registrations,
                         department=admin_dept)


# =============================================
# TEACHER MANAGEMENT
# =============================================
@bp.route('/teachers')
@login_required
def manage_teachers():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    teachers = Teacher.query.filter_by(department_id=admin_dept.department_id).all()
    
    return render_template('department_admin/teachers.html', 
                         teachers=teachers, 
                         department=admin_dept)


# =============================================
# CREATE TEACHER
# =============================================
@bp.route('/teachers/create', methods=['GET', 'POST'])
@login_required
def create_teacher():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    # Get majors for this department
    majors = Major.query.filter_by(department_id=admin_dept.department_id, is_active=True).all()
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        title = request.form.get('title', 'Instructor')
        major_id = request.form.get('teacher_major_id')
        research_area = request.form.get('research_area', '')
        certifications = request.form.get('certifications', '')
        office_location = request.form.get('office_location', '')
        office_phone = request.form.get('office_phone', '')
        education = request.form.get('education', '')
        date_of_birth = request.form.get('teacher_dob')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('dept_admin.create_teacher'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('dept_admin.create_teacher'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('dept_admin.create_teacher'))
        
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='teacher',
            is_active=True,
            created_at=datetime.utcnow()
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        teacher = Teacher(
            teacher_id=user.user_id,
            employee_number=f"EMP{datetime.now().year}{user.user_id:04d}",
            department_id=admin_dept.department_id,
            title=title,
            major_id=int(major_id) if major_id else None,
            research_area=research_area,
            certifications=certifications,
            office_location=office_location,
            office_phone=office_phone,
            education=education,
            date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
            hire_date=date.today(),
            is_department_admin=False
        )
        db.session.add(teacher)
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='CREATE_TEACHER',
            entity_type='user',
            entity_id=user.user_id,
            details=f"Created teacher {username} in {admin_dept.department_name}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        flash(f'Teacher {username} created successfully! Password: {password}', 'success')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    return render_template('department_admin/create_teacher.html', 
                         department=admin_dept, 
                         majors=majors)


# =============================================
# EDIT TEACHER
# =============================================
@bp.route('/teachers/<int:teacher_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_teacher(teacher_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if teacher.department_id != admin_dept.department_id:
        flash('Teacher not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    # Get majors for this department
    majors = Major.query.filter_by(department_id=admin_dept.department_id, is_active=True).all()
    
    if request.method == 'POST':
        user = teacher.user
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.email = request.form['email']
        
        new_password = request.form.get('password')
        if new_password:
            if len(new_password) >= 6:
                user.set_password(new_password)
                flash(f'Password changed for {user.username}', 'info')
            else:
                flash('Password must be at least 6 characters', 'danger')
                return redirect(url_for('dept_admin.edit_teacher', teacher_id=teacher_id))
        
        teacher.title = request.form.get('title', 'Instructor')
        teacher.major_id = int(request.form.get('teacher_major_id')) if request.form.get('teacher_major_id') else None
        teacher.research_area = request.form.get('research_area', '')
        teacher.certifications = request.form.get('certifications', '')
        teacher.office_location = request.form.get('office_location', '')
        teacher.office_phone = request.form.get('office_phone', '')
        teacher.education = request.form.get('education', '')
        
        date_of_birth = request.form.get('teacher_dob')
        if date_of_birth:
            teacher.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        
        db.session.commit()
        flash(f'Teacher {user.username} updated successfully!', 'success')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    return render_template('department_admin/edit_teacher.html', 
                         teacher=teacher, 
                         department=admin_dept,
                         majors=majors)


# =============================================
# DELETE TEACHER
# =============================================
@bp.route('/teachers/<int:teacher_id>/delete', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if teacher.department_id != admin_dept.department_id:
        flash('Teacher not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    sections = CourseSection.query.filter_by(teacher_id=teacher_id).count()
    if sections > 0:
        flash(f'Cannot delete: Teacher is assigned to {sections} section(s).', 'danger')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    username = teacher.user.username
    db.session.delete(teacher.user)
    db.session.commit()
    flash(f'Teacher {username} deleted successfully!', 'success')
    return redirect(url_for('dept_admin.manage_teachers'))


# =============================================
# CREATE STUDENT
# =============================================
@bp.route('/students/create', methods=['GET', 'POST'])
@login_required
def create_student():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    majors = Major.query.filter_by(department_id=admin_dept.department_id, is_active=True).all()
    
    if request.method == 'POST':
        first_name = request.form['first_name'].strip().lower()
        last_name = request.form['last_name'].strip().lower()
        email = request.form['email']
        major_id = request.form.get('major_id')
        enrollment_year = request.form.get('enrollment_year', datetime.now().year)
        date_of_birth = request.form.get('date_of_birth')
        phone_number = request.form.get('phone_number')
        
        username = first_name
        default_password = f"{first_name}123"
        
        original_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{original_username}{counter}"
            counter += 1
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('dept_admin.create_student'))
        
        if len(default_password) < 6:
            default_password = default_password + "123"
        
        user = User(
            username=username,
            email=email,
            first_name=first_name.capitalize(),
            last_name=last_name.capitalize(),
            role='student',
            is_active=True,
            created_at=datetime.utcnow()
        )
        user.set_password(default_password)
        db.session.add(user)
        db.session.flush()
        
        year = datetime.now().year
        student_number = f"STU{year}{user.user_id:04d}"
        
        student = Student(
            student_id=user.user_id,
            student_number=student_number,
            major_id=int(major_id) if major_id else None,
            enrollment_year=int(enrollment_year),
            total_credits=0,
            gpa=0,
            date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None,
            phone_number=phone_number
        )
        db.session.add(student)
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='CREATE_STUDENT',
            entity_type='user',
            entity_id=user.user_id,
            details=f"Created student {username} in {admin_dept.department_name} department",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Student created successfully!', 'success')
        flash(f'📋 Login Credentials:', 'info')
        flash(f'   Username: {username}', 'info')
        flash(f'   Password: {default_password}', 'info')
        flash(f'   Email: {email}', 'info')
        
        return redirect(url_for('dept_admin.manage_students'))
    
    current_year = datetime.now().year
    
    return render_template('department_admin/create_student.html', 
                         department=admin_dept, 
                         majors=majors,
                         current_year=current_year)


# =============================================
# EDIT STUDENT
# =============================================
@bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    majors = Major.query.filter_by(department_id=admin_dept.department_id, is_active=True).all()
    
    if not student.major_obj or student.major_obj.department_id != admin_dept.department_id:
        flash('Student not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_students'))
    
    if request.method == 'POST':
        user = student.user
        if user:
            user.first_name = request.form['first_name']
            user.last_name = request.form['last_name']
            user.email = request.form['email']
            
            new_password = request.form.get('password')
            if new_password:
                if len(new_password) >= 6:
                    user.set_password(new_password)
                    flash(f'Password changed for {user.username}', 'info')
                else:
                    flash('Password must be at least 6 characters', 'danger')
                    return redirect(url_for('dept_admin.edit_student', student_id=student_id))
        
        student.major_id = int(request.form.get('major_id')) if request.form.get('major_id') else None
        student.enrollment_year = int(request.form.get('enrollment_year', student.enrollment_year))
        
        date_of_birth = request.form.get('date_of_birth')
        if date_of_birth:
            student.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
        student.phone_number = request.form.get('phone_number')
        
        db.session.commit()
        flash(f'Student {user.username if user else "Unknown"} updated successfully!', 'success')
        return redirect(url_for('dept_admin.manage_students'))
    
    return render_template('department_admin/edit_student.html', 
                         student=student, 
                         department=admin_dept,
                         majors=majors)


# =============================================
# DELETE STUDENT
# =============================================
@bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
def delete_student(student_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    student = Student.query.get_or_404(student_id)
    
    if not student.major_obj or student.major_obj.department_id != admin_dept.department_id:
        flash('Student not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_students'))
    
    registrations = Registration.query.filter_by(student_id=student_id).count()
    if registrations > 0:
        flash(f'Cannot delete: Student has {registrations} course registration(s).', 'danger')
        return redirect(url_for('dept_admin.manage_students'))
    
    username = student.user.username if student.user else f"Student ID {student_id}"
    
    try:
        if student.user:
            db.session.delete(student.user)
        else:
            db.session.delete(student)
        db.session.commit()
        flash(f'Student {username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting student: {str(e)}', 'danger')
    
    return redirect(url_for('dept_admin.manage_students'))


# =============================================
# RESET PASSWORD (Department Admin)
# =============================================
@bp.route('/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Debug prints
    print(f"DEBUG: Resetting password for user: {user.username}, role: {user.role}")
    
    # Check if user is a teacher (including department_admin role)
    # Department admins are also teachers, but we need to check if they are in the same department
    teacher = Teacher.query.filter_by(teacher_id=user_id).first()
    
    if teacher and teacher.department_id == admin_dept.department_id:
        # Teacher found in this department (could be regular teacher or department admin)
        # Allow password reset for teachers (including department admins in same department)
        new_password = request.form.get('new_password')
        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('dept_admin.manage_teachers'))
        
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password for teacher {user.username} has been reset to: {new_password}', 'success')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    # Check if user is a student in this department (via major)
    student = Student.query.filter_by(student_id=user_id).first()
    if student and student.major_obj and student.major_obj.department_id == admin_dept.department_id:
        new_password = request.form.get('new_password')
        if not new_password or len(new_password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('dept_admin.manage_students'))
        
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password for student {user.username} has been reset to: {new_password}', 'success')
        return redirect(url_for('dept_admin.manage_students'))
    
    # If neither teacher nor student in this department
    flash(f'Cannot reset password for user: {user.username}. User not found in your department or has invalid role.', 'danger')
    return redirect(url_for('dept_admin.dashboard'))


@bp.route('/teacher/<int:teacher_id>')
@login_required
def view_teacher(teacher_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if teacher.department_id != admin_dept.department_id:
        flash('Teacher not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_teachers'))
    
    sections = CourseSection.query.filter_by(teacher_id=teacher_id).all()
    
    return render_template('department_admin/teacher_details.html', 
                         teacher=teacher, 
                         sections=sections,
                         department=admin_dept,
                         now=datetime.now())


# =============================================
# COURSE MANAGEMENT
# =============================================
@bp.route('/courses')
@login_required
def manage_courses():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    courses = Course.query.filter_by(department_id=admin_dept.department_id).all()
    
    return render_template('department_admin/courses.html', 
                         courses=courses, 
                         department=admin_dept)


@bp.route('/courses/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    if request.method == 'POST':
        course_code = request.form['course_code'].upper().strip()
        title = request.form['title'].strip()
        credits = int(request.form['credits'])
        description = request.form.get('description', '')
        
        existing_course = Course.query.filter_by(course_code=course_code).first()
        if existing_course:
            flash(f'Course code "{course_code}" already exists! Please use a different code.', 'danger')
            return redirect(url_for('dept_admin.create_course'))
        
        course = Course(
            course_code=course_code,
            title=title,
            credits=credits,
            department_id=admin_dept.department_id,
            description=description
        )
        db.session.add(course)
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='CREATE_COURSE',
            entity_type='course',
            details=f"Created course {course_code} in {admin_dept.department_name}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        try:
            db.session.commit()
            flash(f'Course {course_code} created successfully!', 'success')
            return redirect(url_for('dept_admin.manage_courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating course: {str(e)}', 'danger')
            return redirect(url_for('dept_admin.create_course'))
    
    return render_template('department_admin/create_course.html', department=admin_dept)


@bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.department_id != admin_dept.department_id:
        flash('Course not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_courses'))
    
    if request.method == 'POST':
        course_code = request.form['course_code'].upper().strip()
        title = request.form['title'].strip()
        credits = int(request.form['credits'])
        description = request.form.get('description', '')
        
        existing = Course.query.filter(
            Course.course_code == course_code,
            Course.course_id != course_id
        ).first()
        
        if existing:
            flash(f'Course code "{course_code}" already exists! Please use a different code.', 'danger')
            return redirect(url_for('dept_admin.edit_course', course_id=course_id))
        
        course.course_code = course_code
        course.title = title
        course.credits = credits
        course.description = description
        
        try:
            db.session.commit()
            flash(f'Course {course_code} updated successfully!', 'success')
            return redirect(url_for('dept_admin.manage_courses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating course: {str(e)}', 'danger')
    
    return render_template('department_admin/edit_course.html', course=course, department=admin_dept)


@bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if course.department_id != admin_dept.department_id:
        flash('Course not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_courses'))
    
    sections = CourseSection.query.filter_by(course_id=course_id).count()
    
    if sections > 0:
        flash(f'Cannot delete course "{course.course_code}" because it has {sections} section(s). Delete the sections first.', 'danger')
        return redirect(url_for('dept_admin.manage_courses'))
    
    course_code = course.course_code
    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course_code}" deleted successfully!', 'success')
    return redirect(url_for('dept_admin.manage_courses'))


# =============================================
# SECTION MANAGEMENT
# =============================================
@bp.route('/sections')
@login_required
def manage_sections():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    sections = CourseSection.query.join(Course).filter(
        Course.department_id == admin_dept.department_id
    ).all()
    
    semesters = Semester.query.all()
    teachers = Teacher.query.filter_by(department_id=admin_dept.department_id).all()
    courses = Course.query.filter_by(department_id=admin_dept.department_id).all()
    
    return render_template('department_admin/sections.html', 
                         sections=sections, 
                         courses=courses, 
                         teachers=teachers, 
                         semesters=semesters,
                         department=admin_dept)


@bp.route('/sections/create', methods=['POST'])
@login_required
def create_section():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    course_id = request.form.get('course_id')
    course = Course.query.get(course_id)
    
    if not course or course.department_id != admin_dept.department_id:
        flash('Course not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    section = CourseSection(
        course_id=course_id,
        semester_id=request.form['semester_id'],
        section_number=request.form['section_number'],
        teacher_id=request.form.get('teacher_id') if request.form.get('teacher_id') else None,
        capacity=int(request.form['capacity']),
        status='open'
    )
    db.session.add(section)
    db.session.commit()
    flash(f'Section {section.section_number} created!', 'success')
    return redirect(url_for('dept_admin.manage_sections'))


@bp.route('/sections/<int:section_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_section(section_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    if section.course.department_id != admin_dept.department_id:
        flash('Section not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    courses = Course.query.filter_by(department_id=admin_dept.department_id).all()
    teachers = Teacher.query.filter_by(department_id=admin_dept.department_id).all()
    semesters = Semester.query.all()
    
    if request.method == 'POST':
        section.course_id = request.form['course_id']
        section.semester_id = request.form['semester_id']
        section.section_number = request.form['section_number']
        section.teacher_id = request.form.get('teacher_id') if request.form.get('teacher_id') else None
        section.capacity = int(request.form['capacity'])
        section.status = request.form.get('status', 'open')
        
        db.session.commit()
        flash(f'Section {section.section_number} updated!', 'success')
        return redirect(url_for('dept_admin.manage_sections'))
    
    return render_template('department_admin/edit_section.html', 
                         section=section, 
                         courses=courses, 
                         teachers=teachers, 
                         semesters=semesters,
                         department=admin_dept)


@bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    if section.course.department_id != admin_dept.department_id:
        flash('Section not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    reg_count = Registration.query.filter_by(section_id=section_id).count()
    if reg_count > 0:
        flash(f'Cannot delete: {reg_count} students registered. Cancel instead.', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    timetable_count = Timetable.query.filter_by(section_id=section_id).count()
    if timetable_count > 0:
        flash(f'Cannot delete: Section has {timetable_count} timetable entries. Delete timetables first.', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    db.session.delete(section)
    db.session.commit()
    flash(f'Section {section.section_number} deleted!', 'success')
    return redirect(url_for('dept_admin.manage_sections'))


# =============================================
# REGISTRATIONS
# =============================================
@bp.route('/registrations')
@login_required
def manage_registrations():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    registrations = Registration.query.join(
        CourseSection, Registration.section_id == CourseSection.section_id
    ).join(
        Course, CourseSection.course_id == Course.course_id
    ).join(
        Student, Registration.student_id == Student.student_id
    ).join(
        User, Student.student_id == User.user_id
    ).filter(
        Course.department_id == admin_dept.department_id
    ).order_by(
        Registration.registration_date.desc()
    ).all()
    
    return render_template('department_admin/registrations.html', 
                         registrations=registrations, 
                         department=admin_dept)


# =============================================
# REGISTRATION WINDOWS
# =============================================
@bp.route('/registration-windows')
@login_required
def manage_registration_windows():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    windows = RegistrationWindow.query.all()
    
    valid_windows = []
    for w in windows:
        semester = Semester.query.get(w.semester_id) if w.semester_id else None
        if semester:
            w.semester = semester
            valid_windows.append(w)
        else:
            if w.semester_id:
                print(f"Deleting orphaned window: {w.window_name} (semester_id: {w.semester_id})")
                db.session.delete(w)
    db.session.commit()
    
    semesters = Semester.query.all()
    
    return render_template('department_admin/registration_windows.html', 
                         windows=valid_windows, 
                         semesters=semesters,
                         department=admin_dept,
                         datetime=datetime,
                         Semester=Semester)


@bp.route('/registration-windows/create', methods=['POST'])
@login_required
def create_registration_window():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    try:
        semester_id = request.form['semester_id']
        semester = Semester.query.get(semester_id) if semester_id else None
        semester_name = semester.semester_name if semester else "Unknown"
        
        window = RegistrationWindow(
            semester_id=semester_id,
            window_name=request.form['window_name'],
            start_datetime=datetime.strptime(request.form['start_datetime'], '%Y-%m-%dT%H:%M'),
            end_datetime=datetime.strptime(request.form['end_datetime'], '%Y-%m-%dT%H:%M'),
            priority=int(request.form.get('priority', 0))
        )
        db.session.add(window)
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='CREATE_REG_WINDOW',
            entity_type='registration_window',
            details=f"Created registration window '{window.window_name}' for {semester_name}",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        
        db.session.commit()
        flash(f'Registration window "{window.window_name}" created!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('dept_admin.manage_registration_windows'))


@bp.route('/registration-windows/<int:window_id>/delete', methods=['POST'])
@login_required
def delete_registration_window(window_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    window = RegistrationWindow.query.get_or_404(window_id)
    window_name = window.window_name
    
    db.session.delete(window)
    db.session.commit()
    
    flash(f'Registration window "{window_name}" deleted!', 'success')
    return redirect(url_for('dept_admin.manage_registration_windows'))


@bp.route('/registration-windows/<int:window_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_registration_window(window_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
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
        return redirect(url_for('dept_admin.manage_registration_windows'))
    
    return render_template('department_admin/edit_registration_window.html', 
                         window=window, 
                         semesters=semesters,
                         department=admin_dept)

# =============================================
# TIMETABLE MANAGEMENT (Full CRUD)
# =============================================

@bp.route('/timetables')
@login_required
def manage_timetables():
    """List all timetables for the department"""
    # Debug: Print current user info
    print(f"DEBUG: current_user.id = {current_user.user_id}")
    print(f"DEBUG: current_user.role = {current_user.role}")
    print(f"DEBUG: current_user.username = {current_user.username}")
    
    # Check role first
    if current_user.role != 'department_admin':
        flash(f'Access denied. Your role is {current_user.role}, but department_admin required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    # Get timetables for sections in this department
    timetables = Timetable.query.join(
        CourseSection, Timetable.section_id == CourseSection.section_id
    ).join(
        Course, CourseSection.course_id == Course.course_id
    ).filter(
        Course.department_id == admin_dept.department_id
    ).all()
    
    return render_template('department_admin/timetables.html', 
                         timetables=timetables,
                         department=admin_dept)


@bp.route('/timetables/create-form')
@login_required
def manage_timetables_create_form():
    """Show form to create a new timetable entry"""
    # Debug: Print current user info
    print(f"DEBUG: current_user.id = {current_user.user_id}")
    print(f"DEBUG: current_user.role = {current_user.role}")
    print(f"DEBUG: current_user.username = {current_user.username}")
    
    # Check role first
    if current_user.role != 'department_admin':
        flash(f'Access denied. Your role is {current_user.role}, but department_admin required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    sections = CourseSection.query.join(Course).filter(
        Course.department_id == admin_dept.department_id
    ).all()
    
    classrooms = Classroom.query.filter_by(is_active=True).all()
    
    return render_template('department_admin/create_timetable.html', 
                         sections=sections,
                         classrooms=classrooms,
                         department=admin_dept)


@bp.route('/timetables/create', methods=['POST'])
@login_required
def create_timetable():
    """Create a new timetable entry"""
    # Check role first
    if current_user.role != 'department_admin':
        flash('Access denied. Department admin privileges required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    try:
        section_id = request.form.get('section_id')
        if not section_id:
            flash('Section is required', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        section = CourseSection.query.get(section_id)
        
        if not section:
            flash('Section not found', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        if section.course.department_id != admin_dept.department_id:
            flash('Section not in your department', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        classroom_id = request.form.get('classroom_id')
        if not classroom_id:
            flash('Classroom is required', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        day_of_week = int(request.form['day_of_week'])
        start_time = datetime.strptime(request.form['start_time'], '%H:%M').time()
        end_time = datetime.strptime(request.form['end_time'], '%H:%M').time()
        
        # Check if start time is before end time
        if start_time >= end_time:
            flash('Start time must be before end time', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        # Check if classroom is already booked at this time
        conflicting_classroom = Timetable.query.filter(
            Timetable.classroom_id == classroom_id,
            Timetable.day_of_week == day_of_week,
            Timetable.is_active == True,
            Timetable.start_time < end_time,
            Timetable.end_time > start_time
        ).first()
        
        if conflicting_classroom:
            conflicting_section = conflicting_classroom.section
            flash(f'Classroom is already booked at this time for {conflicting_section.course.course_code} (Section {conflicting_section.section_number})', 'danger')
            return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        # Check if teacher is already booked at this time
        teacher_id = section.teacher_id
        if teacher_id:
            teacher_conflicting = Timetable.query.join(
                CourseSection, Timetable.section_id == CourseSection.section_id
            ).filter(
                CourseSection.teacher_id == teacher_id,
                Timetable.day_of_week == day_of_week,
                Timetable.is_active == True,
                Timetable.start_time < end_time,
                Timetable.end_time > start_time,
                Timetable.section_id != section_id
            ).first()
            
            if teacher_conflicting:
                conflicting_course = teacher_conflicting.section.course
                flash(f'Teacher is already assigned to {conflicting_course.course_code} at this time!', 'danger')
                return redirect(url_for('dept_admin.manage_timetables_create_form'))
        
        timetable = Timetable(
            section_id=section_id,
            classroom_id=classroom_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            week_pattern=request.form.get('week_pattern', 'weekly'),
            is_active=True
        )
        db.session.add(timetable)
        db.session.commit()
        
        flash('Timetable entry created successfully!', 'success')
        return redirect(url_for('dept_admin.manage_timetables'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating timetable: {str(e)}', 'danger')
        return redirect(url_for('dept_admin.manage_timetables_create_form'))


@bp.route('/timetables/<int:timetable_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_timetable(timetable_id):
    """Edit an existing timetable entry"""
    # Check role first
    if current_user.role != 'department_admin':
        flash('Access denied. Department admin privileges required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    # Debug print
    print(f"DEBUG: Editing timetable {timetable_id}")
    print(f"DEBUG: Timetable section course department: {timetable.section.course.department_id}")
    print(f"DEBUG: Admin department: {admin_dept.department_id}")
    
    # Check if section belongs to department
    if not timetable.section or timetable.section.course.department_id != admin_dept.department_id:
        flash('Timetable not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_timetables'))
    
    if request.method == 'POST':
        try:
            # Get form data
            classroom_id = request.form.get('classroom_id')
            day_of_week = int(request.form.get('day_of_week'))
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            
            if not all([classroom_id, start_time_str, end_time_str]):
                flash('All fields are required', 'danger')
                return redirect(url_for('dept_admin.edit_timetable', timetable_id=timetable_id))
            
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Check if start time is before end time
            if start_time >= end_time:
                flash('Start time must be before end time', 'danger')
                return redirect(url_for('dept_admin.edit_timetable', timetable_id=timetable_id))
            
            # Check for conflicting schedule in the same classroom (excluding current)
            conflicting_classroom = Timetable.query.filter(
                Timetable.classroom_id == classroom_id,
                Timetable.day_of_week == day_of_week,
                Timetable.is_active == True,
                Timetable.timetable_id != timetable_id,
                Timetable.start_time < end_time,
                Timetable.end_time > start_time
            ).first()
            
            if conflicting_classroom:
                conflicting_section = conflicting_classroom.section
                flash(f'Classroom is already booked at this time for {conflicting_section.course.course_code} (Section {conflicting_section.section_number})', 'danger')
                return redirect(url_for('dept_admin.edit_timetable', timetable_id=timetable_id))
            
            # Check if teacher is already booked at this time
            teacher_id = timetable.section.teacher_id
            if teacher_id:
                teacher_conflicting = Timetable.query.join(
                    CourseSection, Timetable.section_id == CourseSection.section_id
                ).filter(
                    CourseSection.teacher_id == teacher_id,
                    Timetable.day_of_week == day_of_week,
                    Timetable.is_active == True,
                    Timetable.timetable_id != timetable_id,
                    Timetable.start_time < end_time,
                    Timetable.end_time > start_time
                ).first()
                
                if teacher_conflicting:
                    conflicting_course = teacher_conflicting.section.course
                    flash(f'Teacher is already assigned to {conflicting_course.course_code} at this time!', 'danger')
                    return redirect(url_for('dept_admin.edit_timetable', timetable_id=timetable_id))
            
            # Update timetable
            timetable.classroom_id = classroom_id
            timetable.day_of_week = day_of_week
            timetable.start_time = start_time
            timetable.end_time = end_time
            timetable.week_pattern = request.form.get('week_pattern', 'weekly')
            timetable.is_active = 'is_active' in request.form
            
            db.session.commit()
            flash('Timetable entry updated successfully!', 'success')
            return redirect(url_for('dept_admin.manage_timetables'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating timetable: {str(e)}', 'danger')
            return redirect(url_for('dept_admin.edit_timetable', timetable_id=timetable_id))
    
    # GET request - show edit form
    sections = CourseSection.query.join(Course).filter(
        Course.department_id == admin_dept.department_id
    ).all()
    classrooms = Classroom.query.filter_by(is_active=True).all()
    
    return render_template('department_admin/edit_timetable.html', 
                         timetable=timetable,
                         sections=sections,
                         classrooms=classrooms,
                         department=admin_dept)


@bp.route('/timetables/<int:timetable_id>/delete', methods=['POST'])
@login_required
def delete_timetable(timetable_id):
    """Delete a timetable entry"""
    # Check role first
    if current_user.role != 'department_admin':
        flash('Access denied. Department admin privileges required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    if not timetable.section or timetable.section.course.department_id != admin_dept.department_id:
        flash('Timetable not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_timetables'))
    
    try:
        db.session.delete(timetable)
        db.session.commit()
        flash('Timetable entry deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timetable: {str(e)}', 'danger')
    
    return redirect(url_for('dept_admin.manage_timetables'))


@bp.route('/timetables/<int:timetable_id>/toggle', methods=['POST'])
@login_required
def toggle_timetable(timetable_id):
    """Toggle timetable active status"""
    # Check role first
    if current_user.role != 'department_admin':
        flash('Access denied. Department admin privileges required.', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found. Please contact system administrator.', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    timetable = Timetable.query.get_or_404(timetable_id)
    
    if not timetable.section or timetable.section.course.department_id != admin_dept.department_id:
        flash('Timetable not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_timetables'))
    
    timetable.is_active = not timetable.is_active
    db.session.commit()
    
    status = "activated" if timetable.is_active else "deactivated"
    flash(f'Timetable entry {status} successfully!', 'success')
    
    return redirect(url_for('dept_admin.manage_timetables'))



# =============================================
# SECTION TIMETABLE VIEW
# =============================================
@bp.route('/sections/<int:section_id>/timetable')
@login_required
def section_timetable(section_id):
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    admin_dept = get_admin_department()
    if not admin_dept:
        flash('Department not found', 'danger')
        return redirect(url_for('dept_admin.dashboard'))
    
    section = CourseSection.query.get_or_404(section_id)
    
    if section.course.department_id != admin_dept.department_id:
        flash('Section not in your department', 'danger')
        return redirect(url_for('dept_admin.manage_sections'))
    
    # Redirect to timetables page with section filter
    flash(f'Viewing timetables for {section.course.course_code} - Section {section.section_number}', 'info')
    return redirect(url_for('dept_admin.manage_timetables'))


# =============================================
# CLASSROOM MANAGEMENT
# =============================================
@bp.route('/classrooms')
@login_required
def manage_classrooms():
    if current_user.role != 'department_admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    classrooms = Classroom.query.all()
    return render_template('department_admin/classrooms.html', classrooms=classrooms, department=get_admin_department())