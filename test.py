# debug_users.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Student, Teacher, Department, Major

app = create_app()

with app.app_context():
    print("\n" + "=" * 70)
    print("USER MANAGEMENT DEBUG")
    print("=" * 70)
    
    # Get all users
    users = User.query.order_by(User.user_id).all()
    
    print(f"\nTotal Users: {len(users)}")
    print("-" * 70)
    
    for u in users:
        print(f"\nUser: {u.username} (ID: {u.user_id})")
        print(f"  Role: {u.role}")
        print(f"  Email: {u.email}")
        print(f"  Created: {u.created_at}")
        
        if u.role in ['teacher', 'department_admin']:
            teacher = Teacher.query.filter_by(teacher_id=u.user_id).first()
            if teacher:
                print(f"  Teacher: {teacher.employee_number}")
                print(f"  Department ID: {teacher.department_id}")
                if teacher.department:
                    print(f"  Department: {teacher.department.department_name}")
                else:
                    print("  Department: NOT ASSIGNED!")
            else:
                print("  Teacher: NOT FOUND!")
                
        elif u.role == 'student':
            student = Student.query.filter_by(student_id=u.user_id).first()
            if student:
                print(f"  Student: {student.student_number}")
                print(f"  Major ID: {student.major_id}")
                if student.major_obj:
                    print(f"  Major: {student.major_obj.major_name}")
                else:
                    print("  Major: NOT ASSIGNED!")
            else:
                print("  Student: NOT FOUND!")
    
    print("\n" + "=" * 70)
    print("DEPARTMENTS")
    print("-" * 70)
    
    depts = Department.query.all()
    for d in depts:
        print(f"ID: {d.department_id} | Code: {d.department_code} | Name: {d.department_name}")
    
    print("\n" + "=" * 70)
    print("MAJORS")
    print("-" * 70)
    
    majors = Major.query.all()
    for m in majors:
        print(f"ID: {m.major_id} | Code: {m.major_code} | Name: {m.major_name} | Dept ID: {m.department_id}")
    
    print("\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)