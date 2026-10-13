from app.models import User, JobApplication, Interview
from app.routes.dashboard import dashboard_bp
from app.routes.auth import auth_bp
from app.routes.jobs import jobs_bp
from app.routes.interviews import interviews_bp
from flask import Flask, jsonify
from sqlalchemy import text
from flask_cors import CORS

from config import Config
from app.extensions import db, migrate, jwt, bcrypt


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(interviews_bp)
    app.register_blueprint(dashboard_bp)

    # Allow requests from the Next.js frontend
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                ]
            }
        },
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Home route
    @app.get("/")
    def home():
        return jsonify({
            "message": "Welcome to CareerTrack API",
            "status": "success"
        }), 200

    # Health check route
    @app.get("/api/health")
    def health_check():
        return jsonify({
            "message": "CareerTrack API is running"
        }), 200

    # Database connection test route
    @app.get("/api/db-test")
    def database_test():
        try:
            db.session.execute(text("SELECT 1"))

            return jsonify({
                "message": "Database connection successful"
            }), 200

        except Exception:
            db.session.rollback()
            app.logger.exception(
                "Database connection failed"
            )

            return jsonify({
                "error": "Database connection failed"
            }), 500

    return app
