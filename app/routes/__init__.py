from .auth import auth_bp
from .student import student_bp
from .admin import admin_bp
from .admin_upload import admin_upload_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_upload_bp, url_prefix="/api/admin_upload")
