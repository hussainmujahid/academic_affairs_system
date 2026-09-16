-- database/fix_registration_constraint.sql
-- =============================================
-- FIX: Allow students to re-register after withdrawal
-- =============================================

-- Step 1: Drop the existing unique constraint
ALTER TABLE registrations DROP CONSTRAINT IF EXISTS registrations_student_id_section_id_key;

-- Step 2: Create a partial unique index that only applies to active enrollments
-- This allows a student to have multiple records (dropped, completed, enrolled)
-- but only ONE active enrollment per section
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_registration 
ON registrations (student_id, section_id) 
WHERE status = 'enrolled';

-- Step 3: Verify the fix
SELECT 
    constraint_name, 
    constraint_type 
FROM information_schema.table_constraints 
WHERE table_name = 'registrations';