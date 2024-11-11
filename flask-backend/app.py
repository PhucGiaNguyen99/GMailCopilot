from flask import Flask, redirect, session, render_template, url_for, request
from google_auth_oauthlib.flow import InstalledAppFlow
import os
from dotenv import load_dotenv
import googleapiclient.discovery
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from models.email_model import db, Email
from models.task_model import db, Task
from datetime import timedelta


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management


# Load environment variables from .env file
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Load the Open AI API secret key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define the scope to access Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Configurate the PostgreSQL database URI
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:610199@localhost/email_organizer"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the SQLAlchemy object
db.init_app(app)


# Define a simple test route to verify database connection
@app.route("/test-connection")
def test_connection():
    try:
        # Use SQLAlchemy's engine to connect and fetch table names
        tables = db.engine.table_names()
        return f"Connected to the database successfully! Available tables: {tables}"
    except Exception as e:
        return f"Failed to connect to the database: {str(e)}"


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

    # Fetch and store emails immediately after authorization
    store_emails_in_db(creds)

    return redirect("/welcome")


# Create a separate reauthorize function in case refresh tokens fail
@app.route("/reauthorize")
def reauthorize():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=7001)  # Run local server for user authentication
    session["credentials"] = creds_to_dict(creds)
    return redirect("/welcome")


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


@app.route("/welcome")
def welcome():
    # Retrieve all stored emails from the database
    emails = Email.query.all()

    # Pass the emails to the template to display

    # Display the email metadata
    return render_template("welcome.html", emails=emails)


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


# Routes for task management


# Route to display all tasks
@app.route("/tasks")
def view_tasks():
    tasks = Task.query.all()
    return render_template("tasks.html", tasks=tasks)


# Route to create a new task
# Create a new task given title, description, due_date
@app.route("/tasks/new", methods=["POST"])
def create_task():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description")
        due_date = request.form.get("due_date")

        new_task = Task(title=title, description=description, due_date=due_date)

        db.session.add(new_task)
        db.session.commit()

        return redirect(url_for("view_tasks"))

    return render_template("create_task.html")


# Route to update a task
@app.route("/tasks/<int:task_id>/edit", methods=["POST", "GET"])
def edit_task(task_id):
    # Get the task from given task_id or return 404
    task = Task.query.get_or_404(task_id)
    if request.method == "POST":
        task.title = request.form["title"]
        task.description = request.form.get("description")
        task.due_date = request.form.get("due_date")
        task.completed = "completed" in request.form

        db.session.commit()

        return redirect(url_for("view_tasks"))
    return render_template("edit_task.html", task=task)


# Route to delete a task
@app.route("tasks/<int:task_id/delete", methods=["POST"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("view_tasks"))


# Route to add a task to Google Calendar
@app.route("/tasks/<int:task_id>/add_to_calendar")
def add_task_to_calendar(task_id):
    if "credentials" not in session:
        return redirect(url_for("authorize"))

    task = Task.query.get_or_404(task_id)
    creds = Credentials(**session["credentials"])
    service = googleapiclient.discovery.build("calendar", "v3", credentials=creds)

    event = {
        "summary": task.title,
        "description": task.description,
        "start": {"dateTime": task.due_date.isoformat(), "timeZone": "UTC"},
        "end": {
            "dateTime": (task.due_date + timedelta(hours=1)).isoformat(),
            "timeZone": "UTC",
        },
    }

    event = service.events().insert(calendarId="primary", body=event).execute()
    return redirect(url_for("view_tasks"))





# Run the Flask app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True, port=7000, use_reloader=False)
