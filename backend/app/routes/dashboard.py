from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, func
from app.extensions import db
from app.models import JobApplication, Interview

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard",
)

@dashboard_bp.get("/")
@jwt_required()
def get_dashboard():
    user_id = int(get_jwt_identity())

    total_applications = db.session.scalar(
        select(func.count())
        .select_from(JobApplication)
        .where(JobApplication.user_id == user_id)
    ) or 0

    status_rows = db.session.execute(
        select(JobApplication.status, func.count(JobApplication.id))
        .where(JobApplication.user_id == user_id)
        .group_by(JobApplication.status)
    ).all()

    status_breakdown = {
        "Wishlist": 0,
        "Applied": 0,
        "Interview": 0,
        "Offer": 0,
        "Rejected": 0,
    }

    for status, count in status_rows:
        status_breakdown[status] = count

    total_interviews = db.session.scalar(
        select(func.count())
        .select_from(Interview)
        .join(
            JobApplication,
            Interview.job_application_id == JobApplication.id,
        )
        .where(JobApplication.user_id == user_id)
    ) or 0

    return jsonify({
        "total_applications": total_applications,
        "total_interviews": total_interviews,
        "total_offers": status_breakdown["Offer"],
        "total_rejections": status_breakdown["Rejected"],
        "status_breakdown": status_breakdown,
    }), 200


