# app/models.py
from flask_login import UserMixin
from datetime import datetime
from app import db

# =============================================
# 1. USERS TABLE
# =============================================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, department_admin, teacher, student
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
        
    def get_id(self):
        return str(self.user_id)
    
    def set_password(self, password):
        from app import bcrypt
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        from app import bcrypt
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


# =============================================
# 2. MAJORS TABLE
# =============================================
class Major(db.Model):
    __tablename__ = 'majors'
    
    major_id = db.Column(db.Integer, primary_key=True)
    major_code = db.Column(db.String(20), unique=True, nullable=False)
    major_name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.department_id'))
    description = db.Column(db.Text)
    required_credits = db.Column(db.Integer, default=120)
    is_active = db.Column(db.Boolean, default=True)
    
    department = db.relationship('Department', foreign_keys=[department_id], backref='majors')
    
    def __repr__(self):
        return f"<Major {self.major_code}>"


# =============================================
# 3. DEPARTMENTS TABLE
# =============================================
class Department(db.Model):
    __tablename__ = 'departments'
    
    department_id = db.Column(db.Integer, primary_key=True)
    department_code = db.Column(db.String(10), unique=True, nullable=False)
    department_name = db.Column(db.String(100), nullable=False)
    dean_id = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'))
    
    dean = db.relationship('Teacher', foreign_keys=[dean_id], backref='dept_managed', uselist=False)
    
    def __repr__(self):
        return f"<Department {self.department_code}>"


# =============================================
# 4. STUDENTS TABLE
# =============================================
class Student(db.Model):
    __tablename__ = 'students'
    
    student_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey('majors.major_id'))
    enrollment_year = db.Column(db.Integer)
    total_credits = db.Column(db.Integer, default=0)
    gpa = db.Column(db.Numeric(3, 2), default=0)
    date_of_birth = db.Column(db.Date)
    phone_number = db.Column(db.String(20))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[student_id], uselist=False, backref='student_profile')
    major_obj = db.relationship('Major', foreign_keys=[major_id], backref='students')
    
    def __repr__(self):
        return f"<Student {self.student_number}>"


# =============================================
# 5. TEACHERS TABLE (with cascade)
# =============================================
class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True)
    employee_number = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.department_id'))
    title = db.Column(db.String(50))  # Professor, Associate Professor, Assistant Professor, Lecturer
    major_id = db.Column(db.Integer, db.ForeignKey('majors.major_id'))  # Foreign key to Major table
    research_area = db.Column(db.Text)  # Research interests/areas
    certifications = db.Column(db.Text)  # Comma-separated or JSON certifications
    date_of_birth = db.Column(db.Date)
    hire_date = db.Column(db.Date)
    office_location = db.Column(db.String(100))
    office_phone = db.Column(db.String(20))
    is_department_admin = db.Column(db.Boolean, default=False)
    education = db.Column(db.Text)  # Educational background
    publications = db.Column(db.Text)  # Key publications
    
    # Relationships
    user = db.relationship('User', foreign_keys=[teacher_id], uselist=False, backref='teacher_profile')
    department = db.relationship('Department', foreign_keys=[department_id], backref='teachers')
    major_obj = db.relationship('Major', foreign_keys=[major_id], backref='teachers')  # Relationship to Major
    
    @property
    def display_name(self):
        if self.user and self.user.first_name:
            return self.user.full_name
        return f"Teacher {self.employee_number}"
    
    @property
    def major_name(self):
        """Convenience property to get major name"""
        return self.major_obj.major_name if self.major_obj else None
    
    def __repr__(self):
        return f"<Teacher {self.employee_number}>"


# =============================================
# 6. COURSES TABLE
# =============================================
class Course(db.Model):
    __tablename__ = 'courses'
    
    course_id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.department_id'))
    
    department = db.relationship('Department', foreign_keys=[department_id], backref='courses')
    
    def __repr__(self):
        return f"<Course {self.course_code}>"


# =============================================
# 7. SEMESTERS TABLE
# =============================================
class Semester(db.Model):
    __tablename__ = 'semesters'
    
    semester_id = db.Column(db.Integer, primary_key=True)
    semester_code = db.Column(db.String(10), unique=True, nullable=False)
    semester_name = db.Column(db.String(50), nullable=False)  # Fall, Spring, Summer
    year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<Semester {self.semester_name} {self.year}>"


# =============================================
# 8. REGISTRATION_WINDOWS TABLE
# =============================================
class RegistrationWindow(db.Model):
    __tablename__ = 'registration_windows'
    
    window_id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.semester_id'), nullable=False)
    window_name = db.Column(db.String(50), nullable=False)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    priority = db.Column(db.Integer, default=0)
    
    semester = db.relationship('Semester', foreign_keys=[semester_id], backref='registration_windows')
    
    def __repr__(self):
        return f"<RegistrationWindow {self.window_name}>"


# =============================================
# 9. CLASSROOM TABLE
# =============================================
class Classroom(db.Model):
    __tablename__ = 'classrooms'
    
    classroom_id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    building = db.Column(db.String(100))
    capacity = db.Column(db.Integer, default=30)
    room_type = db.Column(db.String(50))  # Lecture Hall, Lab, Seminar Room, etc.
    has_projector = db.Column(db.Boolean, default=False)
    has_computers = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<Classroom {self.room_number}>"


# =============================================
# 10. COURSE_SECTIONS TABLE
# =============================================
class CourseSection(db.Model):
    __tablename__ = 'course_sections'
    
    section_id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.semester_id'), nullable=False)
    section_number = db.Column(db.String(5), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'))
    capacity = db.Column(db.Integer, nullable=False)
    enrolled_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='open')  # open, closed, cancelled
    
    __table_args__ = (
        db.UniqueConstraint('course_id', 'semester_id', 'section_number'),
    )
    
    # Relationships
    course = db.relationship('Course', foreign_keys=[course_id], backref='sections')
    semester = db.relationship('Semester', foreign_keys=[semester_id], backref='sections')
    teacher = db.relationship('Teacher', foreign_keys=[teacher_id], backref='sections')
    
    def __repr__(self):
        return f"<CourseSection {self.section_number}>"


# =============================================
# 11. TIMETABLE TABLE
# =============================================
class Timetable(db.Model):
    __tablename__ = 'timetables'
    
    timetable_id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.section_id'), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classrooms.classroom_id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    week_pattern = db.Column(db.String(20), default='weekly')  # weekly, biweekly, odd, even
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('classroom_id', 'day_of_week', 'start_time', name='unique_classroom_time'),
    )
    
    # Relationships
    section = db.relationship('CourseSection', foreign_keys=[section_id], backref='timetables')
    classroom = db.relationship('Classroom', foreign_keys=[classroom_id], backref='timetables')
    
    def __repr__(self):
        return f"<Timetable {self.section_id} - Day {self.day_of_week}>"


# =============================================
# 12. STUDY PLAN TABLE
# =============================================
class StudyPlan(db.Model):
    __tablename__ = 'study_plans'
    
    plan_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    major_id = db.Column(db.Integer, db.ForeignKey('majors.major_id'), nullable=False)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.semester_id'))
    plan_name = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.Integer)
    semester_number = db.Column(db.Integer)  # 1st semester, 2nd semester, etc.
    status = db.Column(db.String(20), default='active')  # active, completed, archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', foreign_keys=[student_id], backref='study_plans')
    major = db.relationship('Major', foreign_keys=[major_id], backref='study_plans')
    semester = db.relationship('Semester', foreign_keys=[semester_id])
    
    def __repr__(self):
        return f"<StudyPlan {self.plan_name}>"


# =============================================
# 13. STUDY PLAN COURSES (Junction for Study Plan)
# =============================================
class StudyPlanCourse(db.Model):
    __tablename__ = 'study_plan_courses'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plans.plan_id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.course_id'), nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    semester_offered = db.Column(db.Integer)  # Which semester in the plan (1-8)
    status = db.Column(db.String(20), default='planned')  # planned, in_progress, completed
    
    # Relationships
    plan = db.relationship('StudyPlan', foreign_keys=[plan_id], backref='courses')
    course = db.relationship('Course', foreign_keys=[course_id])
    
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'course_id', name='unique_plan_course'),
    )
    
    def __repr__(self):
        return f"<StudyPlanCourse Plan:{self.plan_id} Course:{self.course_id}>"


# =============================================
# 14. STUDY PLAN RESEARCH (Research linked to study plan)
# =============================================
class StudyPlanResearch(db.Model):
    __tablename__ = 'study_plan_research'
    
    research_id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('study_plans.plan_id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    research_type = db.Column(db.String(50))  # thesis, project, paper, capstone
    supervisor_id = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='proposed')  # proposed, approved, in_progress, completed
    grade = db.Column(db.Numeric(5, 2))
    submission_date = db.Column(db.Date)
    
    # Relationships
    plan = db.relationship('StudyPlan', foreign_keys=[plan_id], backref='researches')
    supervisor = db.relationship('Teacher', foreign_keys=[supervisor_id], backref='supervised_research')
    
    def __repr__(self):
        return f"<StudyPlanResearch {self.title}>"


# =============================================
# 15. REGISTRATIONS TABLE
# =============================================
class Registration(db.Model):
    __tablename__ = 'registrations'
    
    registration_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.section_id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='enrolled')
    regular_grade = db.Column(db.Numeric(5, 2))
    final_grade = db.Column(db.Numeric(5, 2))
    grade = db.Column(db.Numeric(5, 2))
    drop_date = db.Column(db.DateTime)
    drop_reason = db.Column(db.Text)
    
    __table_args__ = (
        db.UniqueConstraint('student_id', 'section_id'),
    )
    
    # Relationships
    student = db.relationship('Student', foreign_keys=[student_id], backref='registrations')
    section = db.relationship('CourseSection', foreign_keys=[section_id], backref='registrations')
    
    # Use back_populates to match GradeAudit
    grade_audits = db.relationship('GradeAudit', foreign_keys='GradeAudit.registration_id', 
                                   back_populates='registration', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Registration {self.registration_id}>"
    

# =============================================
# 16. ATTENDANCE TABLE
# =============================================
class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    attendance_id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.registration_id'), nullable=False)
    class_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # present, absent, late, excused
    remarks = db.Column(db.Text)
    marked_by = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('registration_id', 'class_date'),
    )
    
    # Relationships
    registration = db.relationship('Registration', foreign_keys=[registration_id], backref='attendance_records')
    teacher = db.relationship('Teacher', foreign_keys=[marked_by], backref='marked_attendance')
    
    def __repr__(self):
        return f"<Attendance {self.attendance_id}>"


# =============================================
# 17. GRADE_AUDIT TABLE (with Foreign Key)
# =============================================
class GradeAudit(db.Model):
    __tablename__ = 'grade_audit'
    
    audit_id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.registration_id'), nullable=False)
    old_grade = db.Column(db.Numeric(5, 2))
    new_grade = db.Column(db.Numeric(5, 2))
    changed_by = db.Column(db.String(50))
    change_reason = db.Column(db.String(100))
    change_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship - use back_populates instead of backref to avoid conflict
    registration = db.relationship('Registration', foreign_keys=[registration_id], back_populates='grade_audits')
    
    def __repr__(self):
        return f"<GradeAudit {self.audit_id}>"


# =============================================
# 18. WAITLIST TABLE
# =============================================
class Waitlist(db.Model):
    __tablename__ = 'waitlist'
    
    waitlist_id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.Integer, db.ForeignKey('course_sections.section_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    position = db.Column(db.Integer)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('section_id', 'student_id'),
    )
    
    # Relationships
    section = db.relationship('CourseSection', foreign_keys=[section_id], backref='waitlist')
    student = db.relationship('Student', foreign_keys=[student_id], backref='waitlist_entries')
    
    def __repr__(self):
        return f"<Waitlist {self.waitlist_id}>"


# =============================================
# 19. COURSE_EVALUATIONS TABLE
# =============================================
class CourseEvaluation(db.Model):
    __tablename__ = 'course_evaluations'
    
    evaluation_id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.registration_id'), nullable=False)
    rating = db.Column(db.Integer)
    comments = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('registration_id'),
    )
    
    # Relationships
    registration = db.relationship('Registration', foreign_keys=[registration_id], backref='evaluation')
    
    def __repr__(self):
        return f"<CourseEvaluation {self.evaluation_id}>"


# =============================================
# 20. SYSTEM_LOGS TABLE
# =============================================
class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', foreign_keys=[user_id], backref='logs')
    
    def __repr__(self):
        return f"<SystemLog {self.log_id}>"