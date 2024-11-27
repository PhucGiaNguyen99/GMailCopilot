from flask import Blueprint, Flask, redirect, session, render_template, url_for, request
from google_auth_oauthlib.flow import InstalledAppFlow
import os
from dotenv import load_dotenv
import googleapiclient.discovery
from flask_sqlalchemy import SQLAlchemy
from config import Config
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from models.email_model import Email
from models.task_model import Task
from datetime import timedelta
from extensions import db  # Import db from extensions
# from routes.auth_routes import auth_bp  # Import the Blueprint

# Define the scope to access Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Create a Blueprint
auth_bp=Blueprint("auth", __name__)

# Convert credentials to a dictionary for session storage
def creds_to_dict(creds):
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

# Authorization route: Redirects the user to Google to authenticate
@auth_bp.route("/authorize", methods=["GET"])
def authorize():
    # Check if credentials are already stored in the session
    if "credentials" in session:
        creds = Credentials(**session["credentials"])

        # If credentials have expired, refresh them
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # If there are no valid credentials, reauthorize
                return redirect(url_for("reauthorize"))

        # Update the session with refreshed credentials
        session["credentials"] = creds_to_dict(creds)
    else:
        # If no credentials in session, initiate new authorization flow
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=7001)  # User authentication
        session["credentials"] = creds_to_dict(creds)

    # Fetch and store emails immediately after authorization
    store_emails_in_db(creds)

    return redirect("/auth/welcome")


# Create a separate reauthorize function in case refresh tokens fail
@auth_bp.route("/reauthorize", methods=["GET"])
def reauthorize():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=7001)  # Run local server for user authentication
    session["credentials"] = creds_to_dict(creds)
    return redirect("/auth/welcome")


# Helper function to store emails
def store_emails_in_db(creds):
    """Fetch and store emails in the database."""
    # Initialize the Gmail API client
    service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

    # Call the Gmail API to get the list of messages
    results = service.users().messages().list(userId="me", maxResults=20).execute()
    messages = results.get("messages", [])

    # Fetch details for each message
    email_data = []
    for msg in messages:
        msg_details = (
            service.users().messages().get(userId="me", id=msg["id"]).execute()
        )

        # Extract the subject and sender fields
        subject = ""
        sender = ""
        for header in msg_details["payload"]["headers"]:
            if header["name"] == "Subject":
                subject = header["value"]
            elif header["name"] == "From":
                sender = header["value"]
            else:
                print(f"Unrecognized header: {header['name']} -> {header['value']}")

        # Check if email already exists in the database by id
        if not Email.query.filter_by(id=msg["id"]).first():
            # Create and save email entry in the database only if it doesn't exist
            email = Email(
                id=msg["id"],
                subject=subject,
                sender=sender,
                snippet=msg_details["snippet"],
                category="Inbox",  # You can update the category field based on your logic
            )
            db.session.add(email)

    db.session.commit()


@auth_bp.route("/welcome", methods=["GET", "POST"])
def welcome():
    sender_name=request.args.get("sender", None)
    # If the filtered name is already entered
    if sender_name:
        emails=Email.query.filter(Email.sender.ilike(f"%{sender_name}%")).all()
    # Otherwise, from the beginning, it shows all the emails
    else:
        emails=Email.query.all()
    return render_template("welcome.html", emails=emails)
