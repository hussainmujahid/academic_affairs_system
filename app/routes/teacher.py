# app/routes/teacher.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.models import (
    Teacher, CourseSection, Registration, Course, 
    Attendance, SystemLog, Semester, Student, Timetable, Classroom
)
from sqlalchemy import text
from datetime import datetime, date, timedelta  
import csv
from io import StringIO

bp = Blueprint('teacher', __name__, url_prefix='/teacher')


# =============================================
# DASHBOARD
# =============================================
@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'teacher':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher:
        flash('Teacher profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Get active semester
    active_semester = Semester.query.filter_by(is_active=True).first()
    
    # Get sections taught by this teacher
    sections = CourseSection.query.filter_by(teacher_id=teacher.teacher_id).all()
    
    section_stats = []
    for section in sections:
        enrolled_count = Registration.query.filter_by(
            section_id=section.section_id, 
            status='enrolled'
        ).count()
        
        # Get timetables for this section
        timetables = Timetable.query.filter_by(section_id=section.section_id, is_active=True).all()
        
        section_stats.append({
            'section': section,
            'enrolled': enrolled_count,
            'capacity': section.capacity,
            'utilization': round(100 * enrolled_count / section.capacity, 2) if section.capacity > 0 else 0,
            'timetables': timetables
        })
    
    return render_template('teacher/dashboard.html', 
                         sections=section_stats, 
                         teacher=teacher,
                         active_semester=active_semester)


# =============================================
# SECTION ROSTER
# =============================================
@bp.route('/section/<int:section_id>/roster')
@login_required
def section_roster(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('You can only view your own sections', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    registrations = Registration.query.filter_by(
        section_id=section_id,
        status='enrolled'
    ).all()
    
    # Get timetables for schedule display
    timetables = Timetable.query.filter_by(section_id=section_id, is_active=True).all()
    
    return render_template('teacher/roster.html', 
                         section=section, 
                         registrations=registrations,
                         timetables=timetables)


# =============================================
# GRADE MANAGEMENT
# =============================================
@bp.route('/section/<int:section_id>/grades', methods=['GET'])
@login_required
def enter_grades(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    registrations = Registration.query.filter_by(section_id=section_id).all()
    
    return render_template('teacher/grades.html', 
                         section=section, 
                         registrations=registrations)


@bp.route('/section/<int:section_id>/grades/save', methods=['POST'])
@login_required
def save_grades(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    saved_count = 0
    
    for key, value in request.form.items():
        if key.startswith('regular_grade_'):
            registration_id = int(key.replace('regular_grade_', ''))
            regular_grade = value
            final_grade = request.form.get(f'final_grade_{registration_id}', '')
            status = request.form.get(f'status_{registration_id}', 'enrolled')
            
            regular_grade = float(regular_grade) if regular_grade else None
            final_grade = float(final_grade) if final_grade else None
            
            # Calculate overall grade
            overall_grade = None
            if regular_grade is not None and final_grade is not None:
                overall_grade = round((regular_grade * 0.3) + (final_grade * 0.7), 2)
            
            registration = Registration.query.get(registration_id)
            if registration:
                registration.regular_grade = regular_grade
                registration.final_grade = final_grade
                registration.grade = overall_grade
                registration.status = status
                
                # If completed, update student's total credits and GPA
                if status == 'completed' and overall_grade and overall_grade >= 60:
                    student = Student.query.get(registration.student_id)
                    if student:
                        student.total_credits = (student.total_credits or 0) + section.course.credits
                        # Recalculate GPA (simplified)
                        all_completed = Registration.query.filter_by(
                            student_id=student.student_id, 
                            status='completed'
                        ).all()
                        total_points = 0
                        total_credits = 0
                        for r in all_completed:
                            if r.grade:
                                if r.grade >= 90:
                                    points = 4.0
                                elif r.grade >= 80:
                                    points = 3.0
                                elif r.grade >= 70:
                                    points = 2.0
                                elif r.grade >= 60:
                                    points = 1.0
                                else:
                                    points = 0.0
                                total_points += points * r.section.course.credits
                                total_credits += r.section.course.credits
                        student.gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0
                
                saved_count += 1
    
    try:
        db.session.commit()
        
        log = SystemLog(
            user_id=current_user.user_id,
            action='UPDATE_GRADES',
            entity_type='section',
            entity_id=section_id,
            details=f"Updated grades for {saved_count} students"
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Grades saved for {saved_count} students!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving grades: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.section_roster', section_id=section_id))


@bp.route('/section/<int:section_id>/grades/export', methods=['GET'])
@login_required
def export_grades(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    registrations = Registration.query.filter_by(section_id=section_id).all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Student ID', 'Student Name', 'Student Number', 'Major',
                     'Regular Grade (30%)', 'Final Grade (70%)', 'Overall Grade', 'Letter Grade', 'Status'])
    
    for reg in registrations:
        grade = reg.grade or 0
        if grade >= 90:
            letter = 'A'
        elif grade >= 80:
            letter = 'B'
        elif grade >= 70:
            letter = 'C'
        elif grade >= 60:
            letter = 'D'
        else:
            letter = 'F' if grade > 0 else 'N/A'
        
        writer.writerow([
            reg.student_id,
            reg.student.user.full_name,
            reg.student.student_number,
            reg.student.major or 'Undeclared',
            reg.regular_grade or '',
            reg.final_grade or '',
            reg.grade or '',
            letter,
            reg.status
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={section.course.course_code}_section{section.section_number}_grades.csv'}
    )


# =============================================
# ATTENDANCE MANAGEMENT
# =============================================
@bp.route('/section/<int:section_id>/attendance', methods=['GET'])
@login_required
def manage_attendance(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    registrations = Registration.query.filter_by(
        section_id=section_id,
        status='enrolled'
    ).all()
    
    # Get class_date from query parameter, default to today
    class_date_str = request.args.get('class_date')
    if class_date_str:
        try:
            current_date = datetime.strptime(class_date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()
    
    prev_date = current_date - timedelta(days=1)
    next_date = current_date + timedelta(days=1)
    today = date.today().isoformat()
    
    # Get attendance records for this date
    attendance_records = {}
    status_counts = {
        'present': 0,
        'absent': 0,
        'late': 0,
        'excused': 0,
        'Total': len(registrations)
    }
    
    for reg in registrations:
        record = Attendance.query.filter_by(
            registration_id=reg.registration_id,
            class_date=current_date
        ).first()
        if record:
            attendance_records[reg.registration_id] = record
            status_name = record.status.lower()
            if status_name in status_counts:
                status_counts[status_name] += 1
    
    # Get timetables for schedule info
    timetables = Timetable.query.filter_by(section_id=section_id, is_active=True).all()
    
    return render_template('teacher/attendance.html',
                         section=section,
                         registrations=registrations,
                         attendance_records=attendance_records,
                         current_date=current_date,
                         prev_date=prev_date.isoformat(),
                         next_date=next_date.isoformat(),
                         today=today,
                         timetables=timetables,
                         status_counts=status_counts)


@bp.route('/section/<int:section_id>/attendance/mark', methods=['POST'])
@login_required
def mark_attendance(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    class_date_str = request.form.get('class_date')
    if not class_date_str:
        flash('Class date is required', 'danger')
        return redirect(url_for('teacher.manage_attendance', section_id=section_id))
    
    class_date = datetime.strptime(class_date_str, '%Y-%m-%d').date()
    saved_count = 0
    
    for key, value in request.form.items():
        if key.startswith('status_'):
            registration_id = int(key.replace('status_', ''))
            status = value
            remarks = request.form.get(f'remarks_{registration_id}', '')
            
            existing = Attendance.query.filter_by(
                registration_id=registration_id,
                class_date=class_date
            ).first()
            
            if existing:
                existing.status = status
                existing.remarks = remarks
                existing.marked_by = teacher.teacher_id
                existing.marked_at = datetime.utcnow()
            else:
                new_attendance = Attendance(
                    registration_id=registration_id,
                    class_date=class_date,
                    status=status,
                    remarks=remarks,
                    marked_by=teacher.teacher_id,
                    marked_at=datetime.utcnow()
                )
                db.session.add(new_attendance)
            saved_count += 1
    
    try:
        db.session.commit()
        flash(f'Attendance saved for {saved_count} students!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving attendance: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.manage_attendance', section_id=section_id, class_date=class_date_str))


@bp.route('/section/<int:section_id>/attendance/report')
@login_required
def attendance_report(section_id):
    section = CourseSection.query.get_or_404(section_id)
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    
    if not teacher or section.teacher_id != teacher.teacher_id:
        flash('Unauthorized', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    registrations = Registration.query.filter_by(section_id=section_id, status='enrolled').all()
    
    attendance_stats = []
    for reg in registrations:
        attendances = Attendance.query.filter_by(registration_id=reg.registration_id).all()
        
        total = len(attendances)
        present = sum(1 for a in attendances if a.status.lower() == 'present')
        absent = sum(1 for a in attendances if a.status.lower() == 'absent')
        late = sum(1 for a in attendances if a.status.lower() == 'late')
        excused = sum(1 for a in attendances if a.status.lower() == 'excused')
        
        percentage = round((present / total * 100), 1) if total > 0 else 0
        
        attendance_stats.append({
            'student': reg.student,
            'registration_id': reg.registration_id,
            'total_classes': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'percentage': percentage
        })
    
    attendance_stats.sort(key=lambda x: x['percentage'])
    
    return render_template('teacher/attendance_report.html',
                         section=section,
                         attendance_stats=attendance_stats)


# =============================================
# API ENDPOINTS
# =============================================
@bp.route('/api/attendance/bulk', methods=['POST'])
@login_required
def bulk_attendance():
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    if not teacher:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    section_id = data.get('section_id')
    class_date_str = data.get('date')
    status = data.get('status')
    
    if not all([section_id, class_date_str, status]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    class_date = datetime.strptime(class_date_str, '%Y-%m-%d').date()
    
    section = CourseSection.query.get(section_id)
    if not section or section.teacher_id != teacher.teacher_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    registrations = Registration.query.filter_by(
        section_id=section_id,
        status='enrolled'
    ).all()
    
    updated_count = 0
    for reg in registrations:
        existing = Attendance.query.filter_by(
            registration_id=reg.registration_id,
            class_date=class_date
        ).first()
        
        if existing:
            existing.status = status
            existing.marked_by = teacher.teacher_id
            existing.marked_at = datetime.utcnow()
        else:
            new_attendance = Attendance(
                registration_id=reg.registration_id,
                class_date=class_date,
                status=status,
                marked_by=teacher.teacher_id,
                marked_at=datetime.utcnow()
            )
            db.session.add(new_attendance)
        updated_count += 1
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': f'Updated {updated_count} records', 'count': updated_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =============================================
# MY SECTIONS
# =============================================
@bp.route('/sections')
@login_required
def my_sections():
    if current_user.role != 'teacher':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    if not teacher:
        flash('Teacher profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    sections = CourseSection.query.filter_by(teacher_id=teacher.teacher_id).all()
    
    # Get timetables for each section
    sections_with_schedule = []
    for section in sections:
        timetables = Timetable.query.filter_by(section_id=section.section_id, is_active=True).all()
        sections_with_schedule.append({
            'section': section,
            'timetables': timetables
        })
    
    return render_template('teacher/sections.html', 
                         sections=sections_with_schedule, 
                         teacher=teacher)


# =============================================
# TEACHER PROFILE
# =============================================
@bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'teacher':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    if not teacher:
        flash('Teacher profile not found', 'danger')
        return redirect(url_for('index.index'))
    
  
    return render_template('teacher/profile.html', teacher=teacher, now=date.today())

# =============================================
# TEACHER TIMETABLE VIEW
# =============================================
@bp.route('/timetable')
@login_required
def view_timetable():
    if current_user.role != 'teacher':
        flash('Access denied', 'danger')
        return redirect(url_for('index.index'))
    
    teacher = Teacher.query.filter_by(teacher_id=current_user.user_id).first()
    if not teacher:
        flash('Teacher profile not found', 'danger')
        return redirect(url_for('index.index'))
    
    # Get all timetables for sections taught by this teacher
    timetables = Timetable.query.join(
        CourseSection, Timetable.section_id == CourseSection.section_id
    ).filter(
        CourseSection.teacher_id == teacher.teacher_id,
        Timetable.is_active == True
    ).order_by(
        Timetable.day_of_week,
        Timetable.start_time
    ).all()
    
    return render_template('teacher/timetable.html', 
                         teacher=teacher, 
                         timetables=timetables)