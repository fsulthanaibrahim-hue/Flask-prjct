
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import select, or_
from app.extensions import db
from app.models import JobApplication


jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


VALID_STATUSES = {
    "Wishlist",
    "Applied",
    "Interview",
    "Offer",
    "Rejected"
}


# CREATE: Add a new job application
@jobs_bp.post("/")
@jwt_required()
def create_job():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A JSON object is required"}), 400

    company_name = data.get("company_name")
    job_title = data.get("job_title")

    if not isinstance(company_name, str) or not company_name.strip():
        return jsonify({"error": "Company name is required"}), 400

    if not isinstance(job_title, str) or not job_title.strip():
        return jsonify({"error": "Job title is required"}), 400

    status = data.get("status", "Wishlist")

    if not isinstance(status, str) or status not in VALID_STATUSES:
        return jsonify({
            "error": "Invalid status",
            "valid_statuses": sorted(VALID_STATUSES)
        }), 400

    for field in ["location", "job_url", "salary", "notes"]:
        value = data.get(field)

        if value is not None and not isinstance(value, str):
            return jsonify({
                "error": f"{field} must be a string or null"
            }), 400

    user_id = int(get_jwt_identity())

    job = JobApplication(
        company_name=company_name.strip(),
        job_title=job_title.strip(),
        location=data.get("location"),
        job_url=data.get("job_url"),
        salary=data.get("salary"),
        status=status,
        notes=data.get("notes"),
        user_id=user_id
    )

    try:
        db.session.add(job)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "message": "Job application created successfully",
        "job": {
            "id": job.id,
            "company_name": job.company_name,
            "job_title": job.job_title,
            "location": job.location,
            "job_url": job.job_url,
            "salary": job.salary,
            "status": job.status,
            "notes": job.notes,
            "application_date": job.application_date.isoformat()
        }
    }), 201


# READ: Get jobs with search, filtering, and pagination
@jobs_bp.get("/")
@jwt_required()
def get_jobs():
    user_id = int(get_jwt_identity())

    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 5, type=int)

    # Validate pagination parameters
    if page is None or page < 1:
        return jsonify({
            "error": "page must be a positive integer"
        }), 400

    if per_page is None or per_page < 1 or per_page > 100:
        return jsonify({
            "error": "per_page must be between 1 and 100"
        }), 400

    # Validate status
    if status and status not in VALID_STATUSES:
        return jsonify({
            "error": "Invalid status",
            "valid_statuses": sorted(VALID_STATUSES)
        }), 400

    # Only retrieve the logged-in user's applications
    query = select(JobApplication).where(
        JobApplication.user_id == user_id
    )

    # Search company name and job title
    if search:
        search_term = f"%{search}%"

        query = query.where(
            or_(
                JobApplication.company_name.ilike(search_term),
                JobApplication.job_title.ilike(search_term)
            )
        )

    # Filter by status
    if status:
        query = query.where(
            JobApplication.status == status
        )

    # Count matching applications before pagination
    count_query = select(db.func.count()).select_from(
        query.order_by(None).subquery()
    )

    total = db.session.scalar(count_query) or 0

    # Retrieve the requested page
    jobs = db.session.scalars(
        query
        .order_by(JobApplication.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    total_pages = (total + per_page - 1) // per_page

    return jsonify({
        "count": len(jobs),
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "jobs": [
            {
                "id": job.id,
                "company_name": job.company_name,
                "job_title": job.job_title,
                "location": job.location,
                "job_url": job.job_url,
                "salary": job.salary,
                "status": job.status,
                "notes": job.notes,
                "application_date": job.application_date.isoformat()
            }
            for job in jobs
        ]
    }), 200


# UPDATE: Edit an existing job application
@jobs_bp.put("/<int:job_id>/")
@jwt_required()
def update_job(job_id):
    user_id = int(get_jwt_identity())

    job = db.session.scalar(
        select(JobApplication).where(
            JobApplication.id == job_id,
            JobApplication.user_id == user_id
        )
    )

    if job is None:
        return jsonify({
            "error": "Job application not found"
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400

    if not data:
        return jsonify({
            "error": "Provide at least one field to update"
        }), 400

    # Update company name
    if "company_name" in data:
        value = data["company_name"]

        if not isinstance(value, str) or not value.strip():
            return jsonify({
                "error": "Company name cannot be empty"
            }), 400

        job.company_name = value.strip()

    # Update job title
    if "job_title" in data:
        value = data["job_title"]

        if not isinstance(value, str) or not value.strip():
            return jsonify({
                "error": "Job title cannot be empty"
            }), 400

        job.job_title = value.strip()

    # Update application status
    if "status" in data:
        value = data["status"]

        if not isinstance(value, str) or value not in VALID_STATUSES:
            return jsonify({
                "error": "Invalid status",
                "valid_statuses": sorted(VALID_STATUSES)
            }), 400

        job.status = value

    # Update optional fields
    for field in ["location", "job_url", "salary", "notes"]:
        if field in data:
            value = data[field]

            if value is not None and not isinstance(value, str):
                return jsonify({
                    "error": f"{field} must be a string or null"
                }), 400

            setattr(job, field, value)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "message": "Job application updated successfully",
        "job": {
            "id": job.id,
            "company_name": job.company_name,
            "job_title": job.job_title,
            "location": job.location,
            "job_url": job.job_url,
            "salary": job.salary,
            "status": job.status,
            "notes": job.notes,
            "application_date": job.application_date.isoformat()
        }
    }), 200


# DELETE: Remove an existing job application
@jobs_bp.delete("/<int:job_id>/")
@jwt_required()
def delete_job(job_id):
    user_id = int(get_jwt_identity())

    job = db.session.scalar(
        select(JobApplication).where(
            JobApplication.id == job_id,
            JobApplication.user_id == user_id
        )
    )

    if job is None:
        return jsonify({
            "error": "Job application not found"
        }), 404

    try:
        db.session.delete(job)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "message": "Job application deleted successfully"
    }), 200
