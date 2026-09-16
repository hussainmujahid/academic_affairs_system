-- database/procedures.sql
-- =============================================
-- STORED PROCEDURES
-- =============================================

CREATE OR REPLACE FUNCTION register_course_advanced(
    p_student_id INTEGER,
    p_course_id INTEGER,
    p_semester VARCHAR
)
RETURNS TABLE(result_message TEXT, success BOOLEAN)
LANGUAGE plpgsql
AS $$
DECLARE
    v_capacity INTEGER;
    v_enrolled INTEGER;
    v_prereq_id INTEGER;
    v_credits INTEGER;
    v_schedule VARCHAR(50);
    v_current_credits INTEGER;
    v_conflict INTEGER;
    v_prereq_passed INTEGER;
BEGIN
    SELECT capacity, enrolled_count, prerequisite_course_id, credits, schedule_time
    INTO v_capacity, v_enrolled, v_prereq_id, v_credits, v_schedule
    FROM courses WHERE course_id = p_course_id FOR UPDATE;
    
    SELECT COUNT(*) INTO v_conflict
    FROM registrations
    WHERE student_id = p_student_id AND course_id = p_course_id AND semester = p_semester;
    
    IF v_conflict > 0 THEN
        result_message := 'Already registered for this course';
        success := FALSE;
        RETURN NEXT;
        RETURN;
    END IF;
    
    IF v_enrolled >= v_capacity THEN
        result_message := 'Course is full';
        success := FALSE;
        RETURN NEXT;
        RETURN;
    END IF;
    
    IF v_prereq_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_prereq_passed
        FROM registrations
        WHERE student_id = p_student_id AND course_id = v_prereq_id AND grade >= 60 AND status = 'completed';
        
        IF v_prereq_passed = 0 THEN
            result_message := 'Prerequisite not met';
            success := FALSE;
            RETURN NEXT;
            RETURN;
        END IF;
    END IF;
    
    SELECT COUNT(*) INTO v_conflict
    FROM registrations r
    JOIN courses c ON r.course_id = c.course_id
    WHERE r.student_id = p_student_id AND r.status = 'enrolled' AND c.semester = p_semester AND c.schedule_time = v_schedule;
    
    IF v_conflict > 0 THEN
        result_message := 'Schedule conflict';
        success := FALSE;
        RETURN NEXT;
        RETURN;
    END IF;
    
    SELECT COALESCE(SUM(c.credits), 0) INTO v_current_credits
    FROM registrations r
    JOIN courses c ON r.course_id = c.course_id
    WHERE r.student_id = p_student_id AND r.status = 'enrolled' AND c.semester = p_semester;
    
    IF (v_current_credits + v_credits) > 20 THEN
        result_message := 'Credit limit exceeded';
        success := FALSE;
        RETURN NEXT;
        RETURN;
    END IF;
    
    INSERT INTO registrations (student_id, course_id, semester, status)
    VALUES (p_student_id, p_course_id, p_semester, 'enrolled');
    
    UPDATE courses SET enrolled_count = enrolled_count + 1 WHERE course_id = p_course_id;
    
    result_message := 'Registration Successful';
    success := TRUE;
    RETURN NEXT;
END;
$$;

CREATE OR REPLACE FUNCTION withdraw_course(
    p_student_id INTEGER,
    p_course_id INTEGER,
    p_semester VARCHAR,
    p_reason TEXT DEFAULT NULL
)
RETURNS TABLE(result_message TEXT, success BOOLEAN)
LANGUAGE plpgsql
AS $$
DECLARE
    v_registration_id INTEGER;
BEGIN
    SELECT registration_id INTO v_registration_id
    FROM registrations
    WHERE student_id = p_student_id AND course_id = p_course_id AND semester = p_semester AND status = 'enrolled';
    
    IF NOT FOUND THEN
        result_message := 'No active registration found';
        success := FALSE;
        RETURN NEXT;
        RETURN;
    END IF;
    
    UPDATE registrations SET status = 'dropped', drop_date = CURRENT_TIMESTAMP, drop_reason = p_reason
    WHERE registration_id = v_registration_id;
    
    UPDATE courses SET enrolled_count = enrolled_count - 1 WHERE course_id = p_course_id;
    
    result_message := 'Withdrawal Successful';
    success := TRUE;
    RETURN NEXT;
END;
$$;

CREATE OR REPLACE FUNCTION archive_semester_grades(p_semester VARCHAR)
RETURNS TABLE(processed_count INTEGER, message TEXT)
LANGUAGE plpgsql
AS $$
DECLARE
    reg_record RECORD;
    calculated_grade DECIMAL;
    v_count INTEGER := 0;
BEGIN
    FOR reg_record IN
        SELECT r.registration_id, r.regular_grade, r.final_grade
        FROM registrations r
        JOIN courses c ON r.course_id = c.course_id
        WHERE c.semester = p_semester AND r.status = 'enrolled'
          AND (r.regular_grade IS NOT NULL OR r.final_grade IS NOT NULL)
    LOOP
        calculated_grade := COALESCE(reg_record.regular_grade, 0) * 0.3 + COALESCE(reg_record.final_grade, 0) * 0.7;
        
        UPDATE registrations SET grade = ROUND(calculated_grade, 2), status = 'completed'
        WHERE registration_id = reg_record.registration_id;
        
        v_count := v_count + 1;
    END LOOP;
    
    processed_count := v_count;
    message := 'Archived ' || v_count || ' grades';
    RETURN NEXT;
END;
$$;