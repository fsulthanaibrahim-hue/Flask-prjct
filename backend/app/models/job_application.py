
from datetime import date

from app.extensions import db


class JobApplication(db.Model):
    __tablename__ = "job_applications"

    id = db.Column(db.Integer, primary_key=True)

    company_name = db.Column(
        db.String(150), nullable=False
    )
    job_title = db.Column(
        db.String(150), nullable=False
    )
    location = db.Column(db.String(150))
    job_url = db.Column(db.String(500))
    salary = db.Column(db.String(100))

    application_date = db.Column(
        db.Date, default=date.today, nullable=False
    )

    status = db.Column(
        db.String(30), default="Wishlist", nullable=False
    )

    notes = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user = db.relationship(
        "User", back_populates="job_applications"
    )

    interviews = db.relationship(
        "Interview",
        back_populates="job_application",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<JobApplication {self.company_name}: {self.job_title}>"
