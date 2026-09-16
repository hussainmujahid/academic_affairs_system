# # init_db.py (Updated - Check before insert)
# import os
# import sys

# print("=" * 60)
# print("SQLite3 Database Setup for Academic System")
# print("=" * 60)

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from app import create_app, db
# from flask_bcrypt import Bcrypt
# from datetime import datetime, date

# app = create_app()
# bcrypt = Bcrypt(app)

# with app.app_context():
#     print("Creating all tables...")
#     db.create_all()
    
#     print("Seeding database...")
    
#     def hash_password(pwd):
#         return bcrypt.generate_password_hash(pwd).decode('utf-8')
    
#     from app.models import User, Student, Teacher, Department, Semester, Course, CourseSection
    
#     # =============================================
#     # CREATE DEPARTMENTS (if not exist)
#     # =============================================
#     print("\n1. Creating departments...")
    
#     cs_dept = Department.query.filter_by(department_code='CS').first()
#     if not cs_dept:
#         cs_dept = Department(department_code='CS', department_name='Computer Science')
#         db.session.add(cs_dept)
#         print("  ✓ Created CS department")
    
#     it_dept = Department.query.filter_by(department_code='IT').first()
#     if not it_dept:
#         it_dept = Department(department_code='IT', department_name='Information Technology')
#         db.session.add(it_dept)
#         print("  ✓ Created IT department")
    
#     db.session.commit()
    
#     # =============================================
#     # CREATE USERS (if not exist)
#     # =============================================
#     print("\n2. Creating users...")
    
#     # Admin user
#     admin = User.query.filter_by(username='admin').first()
#     if not admin:
#         admin = User(
#             username='admin',
#             email='admin@university.edu',
#             password_hash=hash_password('admin123'),
#             first_name='System',
#             last_name='Admin',
#             role='admin',
#             is_active=True,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(admin)
#         print("  ✓ Created admin user")
    
#     # Teacher 1
#     teacher1_user = User.query.filter_by(username='prof_smith').first()
#     if not teacher1_user:
#         teacher1_user = User(
#             username='prof_smith',
#             email='smith@university.edu',
#             password_hash=hash_password('password123'),
#             first_name='John',
#             last_name='Smith',
#             role='teacher',
#             is_active=True,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(teacher1_user)
#         print("  ✓ Created teacher: prof_smith")
#     else:
#         print("  - Teacher prof_smith already exists")
    
#     # Teacher 2
#     teacher2_user = User.query.filter_by(username='dr_johnson').first()
#     if not teacher2_user:
#         teacher2_user = User(
#             username='dr_johnson',
#             email='johnson@university.edu',
#             password_hash=hash_password('password123'),
#             first_name='Robert',
#             last_name='Johnson',
#             role='teacher',
#             is_active=True,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(teacher2_user)
#         print("  ✓ Created teacher: dr_johnson")
#     else:
#         print("  - Teacher dr_johnson already exists")
    
#     # Student 1
#     student1_user = User.query.filter_by(username='john_doe').first()
#     if not student1_user:
#         student1_user = User(
#             username='john_doe',
#             email='john.doe@student.edu',
#             password_hash=hash_password('password123'),
#             first_name='John',
#             last_name='Doe',
#             role='student',
#             is_active=True,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(student1_user)
#         print("  ✓ Created student: john_doe")
#     else:
#         print("  - Student john_doe already exists")
    
#     # Student 2
#     student2_user = User.query.filter_by(username='jane_smith').first()
#     if not student2_user:
#         student2_user = User(
#             username='jane_smith',
#             email='jane.smith@student.edu',
#             password_hash=hash_password('password123'),
#             first_name='Jane',
#             last_name='Smith',
#             role='student',
#             is_active=True,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(student2_user)
#         print("  ✓ Created student: jane_smith")
#     else:
#         print("  - Student jane_smith already exists")
    
#     db.session.commit()
    
#     # =============================================
#     # CREATE TEACHER RECORDS
#     # =============================================
#     print("\n3. Creating teacher records...")
    
#     # Get user IDs after commit
#     teacher1_user = User.query.filter_by(username='prof_smith').first()
#     teacher2_user = User.query.filter_by(username='dr_johnson').first()
    
#     if teacher1_user:
#         teacher1 = Teacher.query.filter_by(teacher_id=teacher1_user.user_id).first()
#         if not teacher1:
#             teacher1 = Teacher(
#                 teacher_id=teacher1_user.user_id,
#                 employee_number='EMP001',
#                 department_id=cs_dept.department_id,
#                 title='Professor',
#                 hire_date=date(2010, 8, 15)
#             )
#             db.session.add(teacher1)
#             print("  ✓ Created teacher record for prof_smith")
#         else:
#             print("  - Teacher record for prof_smith already exists")
    
#     if teacher2_user:
#         teacher2 = Teacher.query.filter_by(teacher_id=teacher2_user.user_id).first()
#         if not teacher2:
#             teacher2 = Teacher(
#                 teacher_id=teacher2_user.user_id,
#                 employee_number='EMP002',
#                 department_id=cs_dept.department_id,
#                 title='Associate Professor',
#                 hire_date=date(2015, 1, 10)
#             )
#             db.session.add(teacher2)
#             print("  ✓ Created teacher record for dr_johnson")
#         else:
#             print("  - Teacher record for dr_johnson already exists")
    
#     # =============================================
#     # CREATE STUDENT RECORDS
#     # =============================================
#     print("\n4. Creating student records...")
    
#     student1_user = User.query.filter_by(username='john_doe').first()
#     student2_user = User.query.filter_by(username='jane_smith').first()
    
#     if student1_user:
#         student1 = Student.query.filter_by(student_id=student1_user.user_id).first()
#         if not student1:
#             student1 = Student(
#                 student_id=student1_user.user_id,
#                 student_number='STU20240001',
#                 major='Computer Science',
#                 enrollment_year=2024,
#                 total_credits=0,
#                 gpa=0
#             )
#             db.session.add(student1)
#             print("  ✓ Created student record for john_doe")
#         else:
#             print("  - Student record for john_doe already exists")
    
#     if student2_user:
#         student2 = Student.query.filter_by(student_id=student2_user.user_id).first()
#         if not student2:
#             student2 = Student(
#                 student_id=student2_user.user_id,
#                 student_number='STU20240002',
#                 major='Software Engineering',
#                 enrollment_year=2024,
#                 total_credits=0,
#                 gpa=0
#             )
#             db.session.add(student2)
#             print("  ✓ Created student record for jane_smith")
#         else:
#             print("  - Student record for jane_smith already exists")
    
#     # =============================================
#     # CREATE SEMESTER
#     # =============================================
#     print("\n5. Creating active semester...")
    
#     active_semester = Semester.query.filter_by(is_active=True).first()
#     if not active_semester:
#         current_year = datetime.now().year
#         active_semester = Semester(
#             semester_code=f"{current_year}-1",
#             semester_name=f"Fall {current_year}",
#             year=current_year,
#             start_date=date(current_year, 9, 1),
#             end_date=date(current_year, 12, 15),
#             is_active=True
#         )
#         db.session.add(active_semester)
#         print(f"  ✓ Created active semester: Fall {current_year}")
#     else:
#         print(f"  - Active semester already exists: {active_semester.semester_name}")
    
#     # =============================================
#     # CREATE COURSES
#     # =============================================
#     print("\n6. Creating courses...")
    
#     courses_data = [
#         {'code': 'CS101', 'title': 'Introduction to Programming', 'credits': 3},
#         {'code': 'CS201', 'title': 'Data Structures', 'credits': 3},
#         {'code': 'CS301', 'title': 'Database Systems', 'credits': 3},
#         {'code': 'CS250', 'title': 'Web Development', 'credits': 3},
#         {'code': 'MATH101', 'title': 'Calculus I', 'credits': 4},
#     ]
    
#     for c_data in courses_data:
#         course = Course.query.filter_by(course_code=c_data['code']).first()
#         if not course:
#             course = Course(
#                 course_code=c_data['code'],
#                 title=c_data['title'],
#                 credits=c_data['credits'],
#                 department_id=cs_dept.department_id,
#                 is_active=True
#             )
#             db.session.add(course)
#             print(f"  ✓ Created course: {c_data['code']}")
#         else:
#             print(f"  - Course already exists: {c_data['code']}")
    
#     db.session.commit()
    
#     # =============================================
#     # CREATE COURSE SECTIONS
#     # =============================================
#     print("\n7. Creating course sections...")
    
#     courses = Course.query.all()
#     teacher = Teacher.query.first()
    
#     section_count = 0
#     for course in courses:
#         existing_section = CourseSection.query.filter_by(
#             course_id=course.course_id,
#             semester_id=active_semester.semester_id
#         ).first()
        
#         if not existing_section and teacher:
#             section = CourseSection(
#                 course_id=course.course_id,
#                 semester_id=active_semester.semester_id,
#                 section_number='A',
#                 teacher_id=teacher.teacher_id,
#                 schedule='Mon/Wed 10:00-11:30',
#                 room='Room 101',
#                 capacity=30,
#                 enrolled_count=0,
#                 status='open'
#             )
#             db.session.add(section)
#             section_count += 1
#             print(f"  ✓ Created section for {course.course_code}")
    
#     db.session.commit()
#     print(f"  Created {section_count} new sections")
    
#     print("\n" + "=" * 60)
#     print("Database setup completed successfully!")
#     print("=" * 60)
#     print("\nLogin Credentials:")
#     print("  Admin:    admin / admin123")
#     print("  Teacher:  prof_smith / password123")
#     print("  Teacher:  dr_johnson / password123")
#     print("  Student:  john_doe / password123")
#     print("  Student:  jane_smith / password123")
#     print("\nRun: python run.py")
#     print("=" * 60)

# init_db.py - Admin Only
import os
import sys

print("=" * 60)
print("SQLite3 Database Setup for Academic System")
print("=" * 60)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from flask_bcrypt import Bcrypt
from datetime import datetime

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    print("Creating all tables...")
    db.create_all()
    
    print("Creating admin user only...")
    
    def hash_password(pwd):
        return bcrypt.generate_password_hash(pwd).decode('utf-8')
    
    from app.models import User
    
    # Create ONLY admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@university.edu',
            password_hash=hash_password('admin123'),
            first_name='System',
            last_name='Admin',
            role='admin',
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        print("  ✓ Created admin user (admin / admin123)")
    else:
        print("  - Admin user already exists")
    
    print("\n" + "=" * 60)
    print("Database setup completed successfully!")
    print("=" * 60)
    print("\nLogin Credentials:")
    print("  Admin:    admin / admin123")
    print("\nAll other tables are empty. Add data through the web interface.")
    print("\nRun: python run.py")
    print("=" * 60)