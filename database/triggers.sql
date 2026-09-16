-- database/triggers.sql
-- =============================================
-- TRIGGERS
-- =============================================

CREATE OR REPLACE FUNCTION log_grade_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF (OLD.grade IS DISTINCT FROM NEW.grade) THEN
        INSERT INTO grade_audit (registration_id, old_grade, new_grade, changed_by)
        VALUES (NEW.registration_id, OLD.grade, NEW.grade, CURRENT_USER);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER grade_change_audit_trigger
    AFTER UPDATE OF grade ON registrations
    FOR EACH ROW
    EXECUTE FUNCTION log_grade_change();

CREATE OR REPLACE FUNCTION update_attendance_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER update_attendance_updated_at_trigger
    BEFORE UPDATE ON attendance
    FOR EACH ROW
    EXECUTE FUNCTION update_attendance_updated_at();