-- database/seed_data.sql
-- =============================================
-- SEED DATA FOR 3NF ACADEMIC AFFAIRS SYSTEM
-- =============================================

-- =============================================
-- 1. USERS
-- =============================================
INSERT INTO users (user_id, username, email, password_hash, first_name, last_name, phone, is_active) VALUES
(1, 'admin', 'admin@university.edu', '$2b$12$LQY3J5Y8K9N2M7P4R6S8T9U1V2W3X4Y5Z6A7B8C9D0E1F2G3H4I5J6K7L8M9', 'System', 'Administrator', '555-0001', true),
(2, 'prof_smith', 'smith@university.edu', '$2b$12$LQY3J5Y8K9N2M7P4R6S8T9U1V2W3X4Y5Z6A7B8C9D0E1F2G3H4I5J6K7L8M9', 'John', 'Smith', '555-0101', true),
(3, 'john_doe', 'john.doe@student.edu', '$2b$12$LQY3J5Y8K9N2M7P4R6S8T9U1V2W3X4Y5Z6A7B8C9D0E1F2G3H4I5J6K7L8M9', 'John', 'Doe', '555-0201', true),
(4, 'jane_smith', 'jane.smith@student.edu', '$2b$12$LQY3J5Y8K9N2M7P4R6S8T9U1V2W3X4Y5Z6A7B8C9D0E1F2G3H4I5J6K7L8M9', 'Jane', 'Smith', '555-0202', true),
(5, 'dr_johnson', 'johnson@university.edu', '$2b$12$LQY3J5Y8K9N2M7P4R6S8T9U1V2W3X4Y5Z6A7B8C9D0E1F2G3H4I5J6K7L8M9', 'Robert', 'Johnson', '555-0102', true);

-- =============================================
-- 2. DEPARTMENTS
-- =============================================
INSERT INTO departments (department_id, department_code, department_name, college, phone, email) VALUES
(1, 'CS', 'Computer Science', 'Engineering', '555-0100', 'cs@university.edu'),
(2, 'MATH', 'Mathematics', 'Sciences', '555-0101', 'math@university.edu'),
(3, 'PHYS', 'Physics', 'Sciences', '555-0102', 'physics@university.edu'),
(4, 'ENG', 'English', 'Humanities', '555-0103', 'english@university.edu'),
(5, 'BUS', 'Business', 'Business School', '555-0104', 'business@university.edu');

-- =============================================
-- 3. TEACHERS (after departments)
-- =============================================
INSERT INTO teachers (teacher_id, employee_number, department_id, title, hire_date, office_location) VALUES
(2, 'EMP001', 1, 'Professor', '2010-08-15', 'Science Building 301'),
(5, 'EMP002', 2, 'Associate Professor', '2015-01-10', 'Math Building 205');

-- =============================================
-- 4. ADMINS
-- =============================================
INSERT INTO admins (admin_id, employee_number, admin_level, department_id, hire_date) VALUES
(1, 'ADM001', 'super_admin', 1, '2018-06-01');

-- =============================================
-- 5. STUDENTS (after departments and teachers for advisor)
-- =============================================
INSERT INTO students (student_id, student_number, major_id, advisor_id, enrollment_date, expected_graduation_date, academic_standing) VALUES
(3, 'STU20240001', 1, 2, '2024-09-01', '2028-05-15', 'good'),
(4, 'STU20240002', 1, 2, '2024-09-01', '2028-05-15', 'good');

-- Update dean references after teachers exist
UPDATE departments SET dean_id = 2 WHERE department_id = 1;
UPDATE departments SET dean_id = 5 WHERE department_id = 2;

-- =============================================
-- 6. BUILDINGS
-- =============================================
INSERT INTO buildings (building_id, building_code, building_name, address) VALUES
(1, 'SCI', 'Science Building', '100 University Ave'),
(2, 'LIB', 'Library', '200 University Ave'),
(3, 'STU', 'Student Center', '300 University Ave'),
(4, 'ENG', 'Engineering Hall', '400 University Ave');

-- =============================================
-- 7. CLASSROOMS
-- =============================================
INSERT INTO classrooms (classroom_id, building_id, room_number, capacity, room_type, has_projector, has_smartboard, has_computers) VALUES
(1, 1, '101', 60, 'lecture', true, true, false),
(2, 1, '102', 40, 'lecture', true, false, false),
(3, 1, '201', 30, 'lab', true, true, true),
(4, 4, '301', 80, 'auditorium', true, true, false),
(5, 2, 'A101', 50, 'seminar', true, true, false);

-- =============================================
-- 8. SEMESTERS
-- =============================================
INSERT INTO semesters (semester_id, semester_code, semester_name, academic_year, season, 
                       start_date, end_date, registration_start, registration_end, 
                       add_drop_deadline, withdraw_deadline, is_active) VALUES
(1, '2026-1', 'Fall 2026', 2026, 'Fall', 
 '2026-09-01', '2026-12-15', 
 '2026-04-01', '2026-08-25', 
 '2026-09-08', '2026-11-01', true),
(2, '2027-1', 'Fall 2027', 2027, 'Fall',
 '2027-09-01', '2027-12-15',
 '2027-04-01', '2027-08-25',
 '2027-09-08', '2027-11-01', false);

-- =============================================
-- 9. COURSES (Core catalog)
-- =============================================
INSERT INTO courses (course_id, course_code, title, credits, description, department_id, is_active) VALUES
(1, 'CS101', 'Introduction to Programming', 3.0, 'Basic programming concepts using Python. Variables, loops, conditionals, functions.', 1, true),
(2, 'CS201', 'Data Structures', 3.0, 'Advanced data structures: arrays, linked lists, stacks, queues, trees, graphs.', 1, true),
(3, 'CS301', 'Database Systems', 3.0, 'Database design, SQL, normalization, transactions.', 1, true),
(4, 'MATH101', 'Calculus I', 4.0, 'Differential calculus: limits, derivatives, applications.', 2, true),
(5, 'MATH102', 'Calculus II', 4.0, 'Integral calculus: integrals, techniques, applications.', 2, true),
(6, 'CS250', 'Web Development', 3.0, 'HTML, CSS, JavaScript, Flask, database integration.', 1, true);

-- =============================================
-- 10. PREREQUISITES (Course dependencies)
-- =============================================
INSERT INTO prerequisites (course_id, prerequisite_course_id, min_grade_required, is_corequisite) VALUES
(2, 1, 60.0, false),  -- CS201 requires CS101 with >=60
(3, 2, 65.0, false),  -- CS301 requires CS201 with >=65
(5, 4, 60.0, false),  -- Calculus II requires Calculus I
(6, 1, 60.0, false);  -- Web Development requires CS101

-- =============================================
-- 11. COURSE_SECTIONS (Offerings per semester)
-- =============================================
INSERT INTO course_sections (section_id, course_id, semester_id, section_number, teacher_id, capacity, enrolled_count, status) VALUES
(1, 1, 1, 'A', 2, 30, 2, 'open'),
(2, 2, 1, 'A', 2, 25, 0, 'open'),
(3, 4, 1, 'A', 5, 30, 0, 'open'),
(4, 6, 1, 'A', 2, 25, 0, 'open');

-- =============================================
-- 12. COURSE_SCHEDULES (Meeting times)
-- =============================================
INSERT INTO course_schedules (schedule_id, section_id, classroom_id, day_of_week, start_time, end_time) VALUES
(1, 1, 1, 'Monday', '10:00:00', '11:30:00'),
(2, 1, 1, 'Wednesday', '10:00:00', '11:30:00'),
(3, 2, 3, 'Tuesday', '13:00:00', '14:30:00'),
(4, 2, 3, 'Thursday', '13:00:00', '14:30:00'),
(5, 3, 2, 'Monday', '15:00:00', '16:30:00'),
(6, 3, 2, 'Wednesday', '15:00:00', '16:30:00'),
(7, 4, 1, 'Friday', '09:00:00', '11:30:00');

-- =============================================
-- 13. GRADE_COMPONENTS
-- =============================================
INSERT INTO grade_components (component_id, component_name, default_weight, description) VALUES
(1, 'Homework', 20, 'Weekly programming assignments'),
(2, 'Quiz', 10, 'Weekly quizzes on lecture material'),
(3, 'Midterm', 30, 'Mid-semester examination'),
(4, 'Final', 40, 'Final examination'),
(5, 'Project', 25, 'Semester-long project');

-- =============================================
-- 14. SECTION_GRADE_COMPONENTS (Custom weights per section)
-- =============================================
INSERT INTO section_grade_components (section_id, component_id, weight, max_points) VALUES
(1, 1, 20, 100),
(1, 2, 10, 50),
(1, 3, 30, 100),
(1, 4, 40, 100),
(2, 1, 15, 100),
(2, 2, 10, 50),
(2, 3, 30, 100),
(2, 4, 45, 100),
(3, 1, 20, 100),
(3, 2, 10, 50),
(3, 3, 30, 100),
(3, 4, 40, 100);

-- =============================================
-- 15. REGISTRATIONS
-- =============================================
INSERT INTO registrations (registration_id, student_id, section_id, registration_date, status) VALUES
(1, 3, 1, CURRENT_TIMESTAMP, 'enrolled'),
(2, 4, 1, CURRENT_TIMESTAMP, 'enrolled');

-- Update enrolled count for section 1
UPDATE course_sections SET enrolled_count = 2 WHERE section_id = 1;

-- =============================================
-- 16. GRADES (Sample grades for John Doe in CS101)
-- =============================================
INSERT INTO grades (registration_id, component_id, score, graded_by, comments) VALUES
(1, 1, 85, 2, 'Good work on assignments'),
(1, 2, 90, 2, 'Excellent quiz performance'),
(1, 3, 78, 2, 'Midterm - need to review recursion'),
(1, 4, NULL, NULL, 'Final pending');

-- =============================================
-- 17. ATTENDANCE_STATUS
-- =============================================
INSERT INTO attendance_status (status_id, status_code, status_name, affects_grade, description) VALUES
(1, 'present', 'Present', false, 'Student attended class'),
(2, 'absent', 'Absent', true, 'Student did not attend'),
(3, 'late', 'Late', true, 'Student arrived late'),
(4, 'excused', 'Excused', false, 'Excused absence'),
(5, 'medical', 'Medical Leave', false, 'Medical leave of absence');

-- =============================================
-- 18. ATTENDANCE (Sample attendance records)
-- =============================================
INSERT INTO attendance (registration_id, class_date, status_id, marked_by) VALUES
(1, '2026-09-02', 1, 2),
(1, '2026-09-04', 1, 2),
(1, '2026-09-07', 1, 2),
(2, '2026-09-02', 1, 2),
(2, '2026-09-04', 3, 2), -- Late once
(2, '2026-09-07', 1, 2);

-- =============================================
-- 19. REGISTRATION_WINDOWS
-- =============================================
INSERT INTO registration_windows (window_id, semester_id, window_type, start_datetime, end_datetime, min_credits, max_credits, eligible_roles, priority) VALUES
(1, 1, 'early_registration', '2026-04-01 00:00:00', '2026-04-15 23:59:59', 12, 21, '["honors","athlete"]', 1),
(2, 1, 'regular_registration', '2026-04-16 00:00:00', '2026-08-25 23:59:59', 12, 21, '["student"]', 2),
(3, 1, 'late_registration', '2026-08-26 00:00:00', '2026-09-08 23:59:59', 9, 18, '["student"]', 3),
(4, 1, 'add_drop', '2026-09-01 00:00:00', '2026-09-08 23:59:59', 9, 21, '["student"]', 4),
(5, 1, 'withdrawal', '2026-09-09 00:00:00', '2026-11-01 23:59:59', 9, 21, '["student"]', 5);

-- =============================================
-- 20. ACADEMIC_CALENDAR
-- =============================================
INSERT INTO academic_calendar (event_id, semester_id, event_date, event_type, event_name, description) VALUES
(1, 1, '2026-09-01', 'registration', 'First Day of Classes', 'Fall semester begins'),
(2, 1, '2026-09-08', 'add_drop', 'Add/Drop Deadline', 'Last day to add/drop courses'),
(3, 1, '2026-10-15', 'exam', 'Midterm Week', 'Mid-semester examinations'),
(4, 1, '2026-11-01', 'withdrawal', 'Withdrawal Deadline', 'Last day to withdraw from courses'),
(5, 1, '2026-11-25', 'holiday', 'Thanksgiving Break', 'University closed'),
(6, 1, '2026-12-07', 'exam', 'Final Exam Week', 'Final examinations begin'),
(7, 1, '2026-12-15', 'other', 'Semester Ends', 'Last day of fall semester');

-- =============================================
-- 21. SYSTEM_LOGS (Initial log)
-- =============================================
INSERT INTO system_logs (user_id, action, entity_type, created_at, ip_address) VALUES
(1, 'database_initialization', 'system', CURRENT_TIMESTAMP, '127.0.0.1');

-- =============================================
-- UPDATE SEQUENCES to continue from max IDs
-- =============================================
SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));
SELECT setval('departments_department_id_seq', (SELECT MAX(department_id) FROM departments));
SELECT setval('buildings_building_id_seq', (SELECT MAX(building_id) FROM buildings));
SELECT setval('classrooms_classroom_id_seq', (SELECT MAX(classroom_id) FROM classrooms));
SELECT setval('semesters_semester_id_seq', (SELECT MAX(semester_id) FROM semesters));
SELECT setval('courses_course_id_seq', (SELECT MAX(course_id) FROM courses));
SELECT setval('course_sections_section_id_seq', (SELECT MAX(section_id) FROM course_sections));
SELECT setval('course_schedules_schedule_id_seq', (SELECT MAX(schedule_id) FROM course_schedules));
SELECT setval('grade_components_component_id_seq', (SELECT MAX(component_id) FROM grade_components));
SELECT setval('registrations_registration_id_seq', (SELECT MAX(registration_id) FROM registrations));
SELECT setval('attendance_status_status_id_seq', (SELECT MAX(status_id) FROM attendance_status));
SELECT setval('registration_windows_window_id_seq', (SELECT MAX(window_id) FROM registration_windows));
SELECT setval('academic_calendar_event_id_seq', (SELECT MAX(event_id) FROM academic_calendar));
SELECT setval('system_logs_log_id_seq', (SELECT MAX(log_id) FROM system_logs));

-- =============================================
-- VERIFICATION QUERIES
-- =============================================

-- Display summary
SELECT 'Database seeded successfully!' as status;
SELECT COUNT(*) as total_users FROM users;
SELECT COUNT(*) as total_students FROM students;
SELECT COUNT(*) as total_teachers FROM teachers;
SELECT COUNT(*) as total_courses FROM courses;
SELECT COUNT(*) as total_sections FROM course_sections;
SELECT COUNT(*) as total_registrations FROM registrations;

-- Show sample data
SELECT u.username, u.first_name, u.last_name, 
       CASE 
           WHEN s.student_id IS NOT NULL THEN 'Student'
           WHEN t.teacher_id IS NOT NULL THEN 'Teacher'
           WHEN a.admin_id IS NOT NULL THEN 'Admin'
       END as role
FROM users u
LEFT JOIN students s ON u.user_id = s.student_id
LEFT JOIN teachers t ON u.user_id = t.teacher_id
LEFT JOIN admins a ON u.user_id = a.admin_id
WHERE u.is_active = true;