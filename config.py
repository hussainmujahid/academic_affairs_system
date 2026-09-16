# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # SQLite3 Database (No server needed - single file)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASE_DIR, "academic_system.db")}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite specific options (no pool_size)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},  # Required for SQLite with multiple threads
    }
    
    # Application Settings
    MAX_CREDITS_PER_SEMESTER = 20
    GRADE_REGULAR_WEIGHT = 0.3
    GRADE_FINAL_WEIGHT = 0.7