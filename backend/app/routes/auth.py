from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from sqlalchemy import select
from app.extensions import db, bcrypt
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "error": "Name, email, and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must contain at least 8 characters"
        }), 400

    existing_user = db.session.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        return jsonify({
            "error": "An account with this email already exists"
        }), 409

    user = User(
        name=name,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8")
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    user = db.session.scalar(
        select(User).where(User.email == email)
    )

    if not user or not bcrypt.check_password_hash(
        user.password_hash, password
    ):
        return jsonify({
            "error": "Invalid email or password"
        }), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }), 200
