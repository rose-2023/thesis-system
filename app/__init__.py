from flask import Flask
from flask_cors import CORS
from .routes.quiz import quiz_bp
from .routes.student import student_bp
from .routes.admin_upload import admin_upload_bp

def create_app():
    app = Flask(__name__)
    # CORS（前端 Vue 用）
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})

# ===== 註冊 blueprint =====
    from .routes.auth import auth_bp
    from .routes.student import student_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(quiz_bp, url_prefix="/api/quiz")
    app.register_blueprint(admin_upload_bp, url_prefix="/api/admin")
    return app
