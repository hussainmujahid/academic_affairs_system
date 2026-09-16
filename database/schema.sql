-- =============================================
-- ACADEMIC AFFAIRS SYSTEM - 3NF DATABASE SCHEMA
-- =============================================

-- =============================================
-- 1. USERS TABLE (Entity)
-- =============================================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+[.][A-Za-z]+$')
);

-- =============================================
-- 2. STUDENTS TABLE (Entity - 3NF)
-- No transitive dependencies - all attributes depend ONLY on student_id
-- =============================================
CREATE TABLE students (
    student_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    student_number VARCHAR(20) UNIQUE NOT NULL,
    major_id INTEGER,
    minor_id INTEGER,
    advisor_id INTEGER,
    enrollment_date DATE NOT NULL,
    expected_graduation_date DATE,
    academic_standing VARCHAR(20) DEFAULT 'good',
    CONSTRAINT chk_academic_standing CHECK (academic_standing IN ('good', 'probation', 'warning', 'suspension', 'graduated')),
    CONSTRAINT chk_enrollment_date CHECK (enrollment_date <= CURRENT_DATE)
);

-- =============================================
-- 3. TEACHERS TABLE (Entity - 3NF)
-- =============================================
CREATE TABLE teachers (
    teacher_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    employee_number VARCHAR(20) UNIQUE NOT NULL,
    department_id INTEGER,
    title VARCHAR(50),
    hire_date DATE NOT NULL,
    office_location VARCHAR(100),
    office_phone VARCHAR(20),
    education_level VARCHAR(50),
    research_interests TEXT,
    CONSTRAINT chk_hire_date CHECK (hire_date <= CURRENT_DATE)
);

-- =============================================
-- 4. ADMINS TABLE (Entity - 3NF)
-- =============================================
CREATE TABLE admins (
    admin_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    employee_number VARCHAR(20) UNIQUE NOT NULL,
    admin_level VARCHAR(20) NOT NULL,
    department_id INTEGER,
    hire_date DATE NOT NULL,
    office_location VARCHAR(100),
    permissions TEXT,
    CONSTRAINT chk_admin_level CHECK (admin_level IN ('super_admin', 'dept_admin', 'support', 'it_admin'))
);

-- =============================================
-- 5. DEPARTMENTS TABLE (Lookup Entity)
-- =============================================
CREATE TABLE departments (
    department_id SERIAL PRIMARY KEY,
    department_code VARCHAR(10) UNIQUE NOT NULL,
    department_name VARCHAR(100) NOT NULL,
    college VARCHAR(100),
    dean_id INTEGER,
    phone VARCHAR(20),
    email VARCHAR(100),
    office_location VARCHAR(100),
    established_year INTEGER,
    CONSTRAINT fk_dean FOREIGN KEY (dean_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL
);

-- Add foreign key references after department table creation
ALTER TABLE students ADD CONSTRAINT fk_student_major FOREIGN KEY (major_id) REFERENCES departments(department_id) ON DELETE SET NULL;
ALTER TABLE students ADD CONSTRAINT fk_student_minor FOREIGN KEY (minor_id) REFERENCES departments(department_id) ON DELETE SET NULL;
ALTER TABLE students ADD CONSTRAINT fk_student_advisor FOREIGN KEY (advisor_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL;
ALTER TABLE teachers ADD CONSTRAINT fk_teacher_dept FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE SET NULL;
ALTER TABLE admins ADD CONSTRAINT fk_admin_dept FOREIGN KEY (department_id) REFERENCES departments(department_id) ON DELETE SET NULL;

-- =============================================
-- 6. SEMESTERS TABLE (Lookup Entity)
-- =============================================
CREATE TABLE semesters (
    semester_id SERIAL PRIMARY KEY,
    semester_code VARCHAR(10) UNIQUE NOT NULL,
    semester_name VARCHAR(50) NOT NULL,
    academic_year INTEGER NOT NULL,
    season VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    registration_start DATE NOT NULL,
    registration_end DATE NOT NULL,
    add_drop_deadline DATE NOT NULL,
    withdraw_deadline DATE NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    CONSTRAINT chk_dates CHECK (start_date < end_date AND registration_start < registration_end),
    CONSTRAINT chk_season CHECK (season IN ('Fall', 'Spring', 'Summer', 'Winter'))
);

-- =============================================
-- 7. BUILDINGS TABLE (Lookup Entity)
-- =============================================
CREATE TABLE buildings (
    building_id SERIAL PRIMARY KEY,
    building_code VARCHAR(10) UNIQUE NOT NULL,
    building_name VARCHAR(100) NOT NULL,
    address VARCHAR(255),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8)
);

-- =============================================
-- 8. CLASSROOMS TABLE (Lookup Entity)
-- =============================================
CREATE TABLE classrooms (
    classroom_id SERIAL PRIMARY KEY,
    building_id INTEGER REFERENCES buildings(building_id) ON DELETE CASCADE,
    room_number VARCHAR(20) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    room_type VARCHAR(30) DEFAULT 'lecture',
    has_projector BOOLEAN DEFAULT FALSE,
    has_smartboard BOOLEAN DEFAULT FALSE,
    has_computers BOOLEAN DEFAULT FALSE,
    UNIQUE(building_id, room_number),
    CONSTRAINT chk_room_type CHECK (room_type IN ('lecture', 'lab', 'seminar', 'auditorium', 'online'))
);

-- =============================================
-- 9. COURSES TABLE (Entity - 3NF)
-- Core course catalog - no semester-specific info
-- =============================================
CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    credits NUMERIC(3,1) NOT NULL CHECK (credits BETWEEN 0.5 AND 6),
    description TEXT,
    department_id INTEGER REFERENCES departments(department_id) ON DELETE SET NULL,
    min_credits INTEGER DEFAULT 0,
    max_credits INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT chk_credits CHECK (min_credits <= credits AND (max_credits IS NULL OR credits <= max_credits))
);

-- =============================================
-- 10. PREREQUISITES TABLE (Relationship - M:M resolution)
-- Resolves many-to-many for course prerequisites
-- =============================================
CREATE TABLE prerequisites (
    prerequisite_id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    prerequisite_course_id INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    min_grade_required DECIMAL(5,2) DEFAULT 60.0,
    is_corequisite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_min_grade CHECK (min_grade_required BETWEEN 0 AND 100),
    CONSTRAINT chk_not_self_prereq CHECK (course_id != prerequisite_course_id),
    UNIQUE(course_id, prerequisite_course_id)
);

-- =============================================
-- 11. COURSE_SECTIONS TABLE (Weak Entity)
-- Section-specific offering of a course in a semester
-- =============================================
CREATE TABLE course_sections (
    section_id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    semester_id INTEGER NOT NULL REFERENCES semesters(semester_id) ON DELETE CASCADE,
    section_number VARCHAR(5) NOT NULL,
    teacher_id INTEGER REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    enrolled_count INTEGER DEFAULT 0 CHECK (enrolled_count <= capacity),
    waitlist_capacity INTEGER DEFAULT 0,
    waitlist_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'open',
    notes TEXT,
    UNIQUE(course_id, semester_id, section_number),
    CONSTRAINT chk_section_status CHECK (status IN ('open', 'closed', 'cancelled', 'waitlist'))
);

-- =============================================
-- 12. COURSE_SCHEDULES TABLE (Weak Entity)
-- Meeting times and locations for course sections
-- =============================================
CREATE TABLE course_schedules (
    schedule_id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES course_sections(section_id) ON DELETE CASCADE,
    classroom_id INTEGER REFERENCES classrooms(classroom_id) ON DELETE SET NULL,
    day_of_week VARCHAR(10) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_online BOOLEAN DEFAULT FALSE,
    meeting_url TEXT,
    UNIQUE(section_id, day_of_week, start_time),
    CONSTRAINT chk_time CHECK (start_time < end_time),
    CONSTRAINT chk_day CHECK (day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'))
);

-- =============================================
-- 13. GRADE_COMPONENTS TABLE (Lookup)
-- Defines grading components (e.g., Homework, Midterm, Final)
-- =============================================
CREATE TABLE grade_components (
    component_id SERIAL PRIMARY KEY,
    component_name VARCHAR(50) NOT NULL,
    default_weight DECIMAL(5,2) NOT NULL CHECK (default_weight BETWEEN 0 AND 100),
    description TEXT,
    UNIQUE(component_name)
);

-- =============================================
-- 14. SECTION_GRADE_COMPONENTS TABLE (Bridge)
-- Links course sections to grade components with weights
-- =============================================
CREATE TABLE section_grade_components (
    section_component_id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES course_sections(section_id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES grade_components(component_id) ON DELETE CASCADE,
    weight DECIMAL(5,2) NOT NULL CHECK (weight BETWEEN 0 AND 100),
    max_points DECIMAL(6,2),
    UNIQUE(section_id, component_id)
);

-- =============================================
-- 15. REGISTRATIONS TABLE (Weak Entity)
-- Student enrollment in course sections
-- =============================================
CREATE TABLE registrations (
    registration_id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES course_sections(section_id) ON DELETE CASCADE,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'enrolled',
    drop_date TIMESTAMP,
    drop_reason TEXT,
    waitlist_position INTEGER,
    CONSTRAINT chk_reg_status CHECK (status IN ('enrolled', 'dropped', 'completed', 'withdrawn', 'incomplete')),
    UNIQUE(student_id, section_id)
);

-- =============================================
-- 16. GRADES TABLE (Weak Entity)
-- Student grades per grade component
-- =============================================
CREATE TABLE grades (
    grade_id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES registrations(registration_id) ON DELETE CASCADE,
    component_id INTEGER NOT NULL REFERENCES grade_components(component_id) ON DELETE CASCADE,
    score DECIMAL(6,2) CHECK (score BETWEEN 0 AND 1000),
    percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN sc.max_points > 0 THEN (score / sc.max_points) * 100
            ELSE score
        END
    ) STORED,
    graded_by INTEGER REFERENCES teachers(teacher_id),
    graded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    comments TEXT,
    UNIQUE(registration_id, component_id)
);

-- =============================================
-- 17. ATTENDANCE_STATUS TABLE (Lookup)
-- =============================================
CREATE TABLE attendance_status (
    status_id SERIAL PRIMARY KEY,
    status_code VARCHAR(20) UNIQUE NOT NULL,
    status_name VARCHAR(50) NOT NULL,
    affects_grade BOOLEAN DEFAULT FALSE,
    description TEXT
);

-- =============================================
-- 18. ATTENDANCE TABLE (Weak Entity)
-- Daily attendance records
-- =============================================
CREATE TABLE attendance (
    attendance_id SERIAL PRIMARY KEY,
    registration_id INTEGER NOT NULL REFERENCES registrations(registration_id) ON DELETE CASCADE,
    class_date DATE NOT NULL,
    status_id INTEGER NOT NULL REFERENCES attendance_status(status_id),
    check_in_time TIME,
    check_out_time TIME,
    marked_by INTEGER REFERENCES teachers(teacher_id),
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(registration_id, class_date)
);

-- =============================================
-- 19. REGISTRATION_WINDOWS TABLE (Lookup/Policy)
-- =============================================
CREATE TABLE registration_windows (
    window_id SERIAL PRIMARY KEY,
    semester_id INTEGER NOT NULL REFERENCES semesters(semester_id) ON DELETE CASCADE,
    window_type VARCHAR(30) NOT NULL,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP NOT NULL,
    min_credits INTEGER DEFAULT 0,
    max_credits INTEGER DEFAULT 21,
    eligible_roles TEXT,
    priority INTEGER DEFAULT 0,
    UNIQUE(semester_id, window_type),
    CONSTRAINT chk_window_time CHECK (start_datetime < end_datetime),
    CONSTRAINT chk_window_type CHECK (window_type IN ('early_registration', 'regular_registration', 'late_registration', 'add_drop', 'withdrawal'))
);

-- =============================================
-- 20. ACADEMIC_CALENDAR TABLE (Lookup)
-- =============================================
CREATE TABLE academic_calendar (
    event_id SERIAL PRIMARY KEY,
    semester_id INTEGER NOT NULL REFERENCES semesters(semester_id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_name VARCHAR(200) NOT NULL,
    description TEXT,
    CONSTRAINT chk_event_type CHECK (event_type IN ('holiday', 'exam', 'registration', 'add_drop', 'withdrawal', 'break', 'other'))
);

-- =============================================
-- 21. GRADE_AUDIT TABLE (Audit Log - Weak Entity)
-- =============================================
CREATE TABLE grade_audit (
    audit_id SERIAL PRIMARY KEY,
    grade_id INTEGER NOT NULL,
    old_score DECIMAL(6,2),
    new_score DECIMAL(6,2),
    changed_by VARCHAR(50),
    change_reason VARCHAR(100),
    change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET
);

-- =============================================
-- 22. SYSTEM_LOGS TABLE (Audit Log)
-- =============================================
CREATE TABLE system_logs (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================
-- CREATE INDEXES FOR PERFORMANCE
-- =============================================

-- Students indexes
CREATE INDEX idx_students_major ON students(major_id);
CREATE INDEX idx_students_advisor ON students(advisor_id);
CREATE INDEX idx_students_enrollment_date ON students(enrollment_date);

-- Course section indexes
CREATE INDEX idx_sections_course ON course_sections(course_id);
CREATE INDEX idx_sections_semester ON course_sections(semester_id);
CREATE INDEX idx_sections_teacher ON course_sections(teacher_id);
CREATE INDEX idx_sections_status ON course_sections(status);

-- Registrations indexes
CREATE INDEX idx_registrations_student ON registrations(student_id);
CREATE INDEX idx_registrations_section ON registrations(section_id);
CREATE INDEX idx_registrations_status ON registrations(status);

-- Grades indexes
CREATE INDEX idx_grades_registration ON grades(registration_id);
CREATE INDEX idx_grades_component ON grades(component_id);

-- Attendance indexes
CREATE INDEX idx_attendance_registration ON attendance(registration_id);
CREATE INDEX idx_attendance_date ON attendance(class_date);
CREATE INDEX idx_attendance_status ON attendance(status_id);

-- Schedule indexes
CREATE INDEX idx_schedules_section ON course_schedules(section_id);
CREATE INDEX idx_schedules_time ON course_schedules(day_of_week, start_time);

-- System logs indexes
CREATE INDEX idx_logs_user ON system_logs(user_id);
CREATE INDEX idx_logs_created ON system_logs(created_at);
CREATE INDEX idx_logs_action ON system_logs(action);