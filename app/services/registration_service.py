# app/services/registration_service.py
from app import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class RegistrationService:
    """Handles all course registration business logic"""
    
    @staticmethod
    def register_course(student_id, course_id, semester, retries=3):
        """
        Register a student for a course with retry logic for high concurrency
        
        Returns:
            dict: {'success': bool, 'message': str, 'data': dict}
        """
        for attempt in range(retries):
            try:
                result = db.session.execute(
                    text("SELECT * FROM register_course_advanced(:student_id, :course_id, :semester)"),
                    {
                        "student_id": student_id,
                        "course_id": course_id,
                        "semester": semester
                    }
                ).first()
                
                db.session.commit()
                
                if result and result.success:
                    return {
                        'success': True,
                        'message': result.result_message,
                        'data': {'registration_id': result.registration_id if hasattr(result, 'registration_id') else None}
                    }
                else:
                    return {
                        'success': False,
                        'message': result.result_message if result else 'Registration failed',
                        'data': None
                    }
                    
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                logger.error(f"Registration attempt {attempt + 1} failed: {error_msg}")
                
                if "course is full" in error_msg.lower():
                    return {'success': False, 'message': 'Course is full', 'retryable': False, 'data': None}
                elif "prerequisite" in error_msg.lower():
                    return {'success': False, 'message': 'Prerequisite not met', 'retryable': False, 'data': None}
                elif "credit limit" in error_msg.lower():
                    return {'success': False, 'message': error_msg, 'retryable': False, 'data': None}
                elif "conflict" in error_msg.lower():
                    return {'success': False, 'message': 'Schedule conflict detected', 'retryable': False, 'data': None}
                elif attempt < retries - 1:
                    continue
                else:
                    return {'success': False, 'message': f'System error: {error_msg}', 'retryable': True, 'data': None}
        
        return {'success': False, 'message': 'Max retries exceeded', 'retryable': False, 'data': None}
    
    @staticmethod
    def withdraw_course(student_id, course_id, semester, reason=None):
        """Withdraw a student from a course"""
        try:
            result = db.session.execute(
                text("SELECT * FROM withdraw_course(:student_id, :course_id, :semester, :reason)"),
                {
                    "student_id": student_id,
                    "course_id": course_id,
                    "semester": semester,
                    "reason": reason or "Student withdrawal"
                }
            ).first()
            
            db.session.commit()
            
            return {
                'success': result.success if result else False,
                'message': result.result_message if result else 'Withdrawal failed'
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Withdrawal error: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def get_student_schedule(student_id, semester=None):
        """Get student's current schedule"""
        try:
            query = """
                SELECT r.registration_id, r.course_id, r.status, r.registration_time,
                       c.course_code, c.title, c.credits, c.schedule_time, c.semester,
                       t.name as teacher_name
                FROM registrations r
                JOIN courses c ON r.course_id = c.course_id
                JOIN teachers t ON c.teacher_id = t.teacher_id
                WHERE r.student_id = :student_id AND r.status = 'enrolled'
            """
            params = {"student_id": student_id}
            
            if semester:
                query += " AND c.semester = :semester"
                params["semester"] = semester
            
            query += " ORDER BY c.schedule_time"
            
            result = db.session.execute(text(query), params).fetchall()
            
            return [dict(row._mapping) for row in result]
        except Exception as e:
            logger.error(f"Error getting schedule: {str(e)}")
            return []
    
    @staticmethod
    def check_registration_eligibility(student_id, course_id, semester):
        """Check if student is eligible to register without actually registering"""
        try:
            # Get course details
            course = db.session.execute(
                text("SELECT capacity, enrolled_count, credits, prerequisite_course_id, schedule_time FROM courses WHERE course_id = :course_id"),
                {"course_id": course_id}
            ).first()
            
            if not course:
                return {'eligible': False, 'reason': 'Course not found'}
            
            # Check capacity
            if course.enrolled_count >= course.capacity:
                return {'eligible': False, 'reason': 'Course is full'}
            
            # Check prerequisites
            if course.prerequisite_course_id:
                prereq_passed = db.session.execute(
                    text("""
                        SELECT COUNT(*) FROM registrations 
                        WHERE student_id = :student_id 
                        AND course_id = :prereq_id 
                        AND grade >= 60 
                        AND status = 'completed'
                    """),
                    {"student_id": student_id, "prereq_id": course.prerequisite_course_id}
                ).scalar()
                
                if prereq_passed == 0:
                    return {'eligible': False, 'reason': 'Prerequisite not met'}
            
            # Check schedule conflict
            conflict = db.session.execute(
                text("""
                    SELECT COUNT(*) FROM registrations r
                    JOIN courses c ON r.course_id = c.course_id
                    WHERE r.student_id = :student_id 
                    AND r.status = 'enrolled'
                    AND c.semester = :semester
                    AND c.schedule_time = :schedule_time
                """),
                {"student_id": student_id, "semester": semester, "schedule_time": course.schedule_time}
            ).scalar()
            
            if conflict > 0:
                return {'eligible': False, 'reason': 'Schedule conflict'}
            
            # Check credit limit
            current_credits = db.session.execute(
                text("""
                    SELECT COALESCE(SUM(c.credits), 0) FROM registrations r
                    JOIN courses c ON r.course_id = c.course_id
                    WHERE r.student_id = :student_id 
                    AND r.status = 'enrolled'
                    AND c.semester = :semester
                """),
                {"student_id": student_id, "semester": semester}
            ).scalar()
            
            if current_credits + course.credits > 20:
                return {'eligible': False, 'reason': f'Credit limit exceeded (Current: {current_credits}, Requesting: {course.credits}, Max: 20)'}
            
            return {'eligible': True, 'reason': None}
            
        except Exception as e:
            logger.error(f"Eligibility check error: {str(e)}")
            return {'eligible': False, 'reason': str(e)}