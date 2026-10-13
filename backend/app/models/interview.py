from app.extensions import db


class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)

    interview_date = db.Column(
        db.DateTime(timezone=True), nullable=False
    )
    interview_round = db.Column(
        db.String(100), nullable=False
    )
    meeting_link = db.Column(db.String(500))
    notes = db.Column(db.Text)

    job_application_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "job_applications.id", ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    job_application = db.relationship(
        "JobApplication", back_populates="interviews"
    )

    def __repr__(self):
        return f"<Interview {self.interview_round}>"
