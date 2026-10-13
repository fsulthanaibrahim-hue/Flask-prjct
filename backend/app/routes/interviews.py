
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.extensions import db
from app.models import Interview, JobApplication


interviews_bp = Blueprint("interviews", __name__, url_prefix="/api")

VALID_INTERVIEW_FIELDS = {
    "interview_date",
    "interview_round",
    "meeting_link",
    "notes",
}


def serialize_interview(interview):
    return {
        "id": interview.id,
        "interview_date": interview.interview_date.isoformat(),
        "interview_round": interview.interview_round,
        "meeting_link": interview.meeting_link,
        "notes": interview.notes,
        "job_application_id": interview.job_application_id,
    }


def parse_interview_date(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Interview date is required.")

    try:
        return datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError:
        raise ValueError(
            "Use a valid ISO date-time, e.g. "
            "2026-11-15T10:30:00."
        )


def get_owned_job(job_id, user_id):
    return db.session.scalar(
        select(JobApplication).where(
            JobApplication.id == job_id,
            JobApplication.user_id == user_id,
        )
    )


def get_owned_interview(interview_id, user_id):
    return db.session.scalar(
        select(Interview)
        .join(
            JobApplication,
            Interview.job_application_id == JobApplication.id,
        )
        .where(
            Interview.id == interview_id,
            JobApplication.user_id == user_id,
        )
    )


def save_changes():
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


# GET: List all interviews for the logged-in user.
@interviews_bp.get("/interviews/")
@jwt_required()
def get_all_interviews():
    user_id = int(get_jwt_identity())

    rows = db.session.execute(
        select(
            Interview,
            JobApplication.company_name,
            JobApplication.job_title,
        )
        .join(
            JobApplication,
            Interview.job_application_id == JobApplication.id,
        )
        .where(JobApplication.user_id == user_id)
        .order_by(Interview.interview_date.asc())
    ).all()

    interviews = []

    for interview, company_name, job_title in rows:
        item = serialize_interview(interview)
        item["company"] = company_name
        item["position"] = job_title
        interviews.append(item)

    return jsonify({
        "total": len(interviews),
        "interviews": interviews,
    }), 200


# POST: Create an interview for a job application.
@interviews_bp.post("/jobs/<int:job_id>/interviews/")
@jwt_required()
def create_interview(job_id):
    user_id = int(get_jwt_identity())
    job = get_owned_job(job_id, user_id)

    if job is None:
        return jsonify({
            "error": "Job application not found."
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A JSON object is required."
        }), 400

    if not data:
        return jsonify({
            "error": "Interview details are required."
        }), 400

    if not VALID_INTERVIEW_FIELDS.issuperset(data.keys()):
        return jsonify({
            "error": "Invalid field provided."
        }), 400

    try:
        interview_date = parse_interview_date(
            data.get("interview_date")
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    interview_round = data.get("interview_round")

    if (
        not isinstance(interview_round, str)
        or not interview_round.strip()
    ):
        return jsonify({
            "error": "Interview round is required."
        }), 400

    meeting_link = data.get("meeting_link")
    notes = data.get("notes")

    if meeting_link is not None and not isinstance(meeting_link, str):
        return jsonify({
            "error": "Meeting link must be a string or null."
        }), 400

    if notes is not None and not isinstance(notes, str):
        return jsonify({
            "error": "Notes must be a string or null."
        }), 400

    interview = Interview(
        interview_date=interview_date,
        interview_round=interview_round.strip(),
        meeting_link=meeting_link.strip() if meeting_link else None,
        notes=notes.strip() if notes else None,
        job_application_id=job.id,
    )

    db.session.add(interview)
    save_changes()

    return jsonify({
        "message": "Interview created successfully.",
        "interview": serialize_interview(interview),
    }), 201


# GET: List interviews for one job application.
@interviews_bp.get("/jobs/<int:job_id>/interviews/")
@jwt_required()
def get_interviews(job_id):
    user_id = int(get_jwt_identity())
    job = get_owned_job(job_id, user_id)

    if job is None:
        return jsonify({
            "error": "Job application not found."
        }), 404

    interviews = db.session.scalars(
        select(Interview)
        .where(Interview.job_application_id == job.id)
        .order_by(Interview.interview_date.asc())
    ).all()

    return jsonify({
        "job_application_id": job.id,
        "total": len(interviews),
        "interviews": [
            serialize_interview(item) for item in interviews
        ],
    }), 200


# PATCH: Update an interview.
@interviews_bp.patch("/interviews/<int:interview_id>/")
@jwt_required()
def update_interview(interview_id):
    user_id = int(get_jwt_identity())
    interview = get_owned_interview(interview_id, user_id)

    if interview is None:
        return jsonify({
            "error": "Interview not found."
        }), 404

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "Provide interview details to update."
        }), 400

    if not VALID_INTERVIEW_FIELDS.issuperset(data.keys()):
        return jsonify({
            "error": "Invalid field provided."
        }), 400

    if "interview_date" in data:
        try:
            interview.interview_date = parse_interview_date(
                data["interview_date"]
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400

    if "interview_round" in data:
        value = data["interview_round"]

        if not isinstance(value, str) or not value.strip():
            return jsonify({
                "error": "Interview round cannot be empty."
            }), 400

        interview.interview_round = value.strip()

    for field in ("meeting_link", "notes"):
        if field in data:
            value = data[field]

            if value is not None and not isinstance(value, str):
                return jsonify({
                    "error": f"{field} must be a string or null."
                }), 400

            setattr(
                interview,
                field,
                value.strip() if value else None,
            )

    save_changes()

    return jsonify({
        "message": "Interview updated successfully.",
        "interview": serialize_interview(interview),
    }), 200


# DELETE: Delete an interview.
@interviews_bp.delete("/interviews/<int:interview_id>/")
@jwt_required()
def delete_interview(interview_id):
    user_id = int(get_jwt_identity())
    interview = get_owned_interview(interview_id, user_id)

    if interview is None:
        return jsonify({
            "error": "Interview not found."
        }), 404

    db.session.delete(interview)
    save_changes()

    return jsonify({
        "message": "Interview deleted successfully."
    }), 200
