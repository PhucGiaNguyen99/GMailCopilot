from flask import Blueprint, request, render_template
from models.email_model import Email 

email_bp=Blueprint("emails", __name__)

@email_bp.route("/filter", methods=["GET"])
def filter_emails():
    sender_name=request.args.get("sender", None)
    if sender_name:
        emails=Email.query.filter(Email.sender.ilike(f"%{sender_name}%")).all()
    else:
        emails=Email.query.all()
    return render_template("emails.html", emails=emails)
