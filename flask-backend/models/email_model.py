from flask_sqlalchemy import SQLAlchemy
from extensions import db


class Email(db.Model):
    __tablename__ = "emails"
    id = db.Column(
        db.String(128), primary_key=True, nullable=False
    )  # Email ID (Primary Key)
    subject = db.Column(db.String(256))  # Email Subject
    sender = db.Column(db.String(256))  # Sender Information
    snippet = db.Column(db.Text)  # Snippet of the email body
    category = db.Column(
        db.String(128)
    )  # Category of the email (e.g., "Work", "Personal")
