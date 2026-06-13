import os


class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-this-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(INSTANCE_DIR, "attendance.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # BASE_URL must be set to the public server URL for external student access
    # Examples:
    #   - College server: http://192.168.1.100:5000 or https://attendance.college.edu
    #   - ngrok tunnel: https://abc123.ngrok.io
    #   - Render.com: https://smart-attendance.onrender.com
    BASE_URL = os.environ.get('BASE_URL', '').strip()
    
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
