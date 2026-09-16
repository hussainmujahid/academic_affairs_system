-- database/indexes.sql
-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

CREATE INDEX CONCURRENTLY idx_registrations_student ON registrations(student_id);
CREATE INDEX CONCURRENTLY idx_registrations_course ON registrations(course_id);
CREATE INDEX CONCURRENTLY idx_registrations_status ON registrations(status);
CREATE INDEX CONCURRENTLY idx_courses_semester ON courses(semester);
CREATE INDEX CONCURRENTLY idx_courses_teacher ON courses(teacher_id);
CREATE INDEX CONCURRENTLY idx_attendance_registration ON attendance(registration_id);
CREATE INDEX CONCURRENTLY idx_attendance_date ON attendance(class_date);