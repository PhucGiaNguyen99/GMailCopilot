from flask import Flask, redirect, session, render_template, url_for
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import googleapiclient.discovery
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Define the scope to access Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# Index route: Checks if the user is authenticated
@app.route("/")
def index():
    if "credentials" not in session:
        return redirect(url_for("authorize"))
    return redirect(url_for("welcome"))


# Authorization route: Redirects the user to Google to authenticate
@app.route("/authorize")
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

    return redirect("/welcome")


# Optional: Create a separate reauthorize function in case refresh tokens fail
@app.route("/reauthorize")
def reauthorize():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=7001)  # Run local server for user authentication
    session["credentials"] = creds_to_dict(creds)
    return redirect("/welcome")


@app.route("/welcome")
def welcome():
    # Render a simple "Welcome" message
    # return "Hello, welcome to the app!"
    # Load the credentials from the session
    creds = Credentials(**session["credentials"])

    # Initialize the Gmail API client
    service = googleapiclient.discovery.build("gmail", "v1", credentials=creds)

    # Call the Gmail API to get the list of messages
    results = service.users().messages().list(userId="me", maxResults=10).execute()
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

        # Store extracted email data
        email_data.append(
            {
                "id": msg["id"],
                "snippet": msg_details["snippet"],
                "subject": subject,
                "sender": sender,
            }
        )

    # Display the email metadata
    return render_template("welcome.html", emails=email_data)


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


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, port=7000, use_reloader=False)
