from flask import Blueprint, render_template, redirect, url_for, jsonify, request, flash
from flask_login import login_required, current_user, login_user
from app import db
from app.models import User, Student, Teacher, Course, Department
from datetime import datetime

bp = Blueprint('index', __name__, url_prefix='/')

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    # Handle login POST request directly on the landing page
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'department_admin':
                return redirect(url_for('dept_admin.dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            else:
                return redirect(url_for('student.dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'department_admin':
            return redirect(url_for('dept_admin.dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
    
    return render_template('index.html')

@bp.route('/api/stats')
def get_stats():
    """API endpoint for homepage statistics"""
    return jsonify({
        'students': Student.query.count(),
        'teachers': Teacher.query.count(),
        'courses': Course.query.count(),
        'departments': Department.query.count()
    })