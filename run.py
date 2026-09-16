# run.py
from app import create_app, db
from app.models import User, Student, Teacher, Course, Registration

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Student': Student,
        'Teacher': Teacher,
        'Course': Course,
        'Registration': Registration
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)