from flask import Flask, redirect, session, render_template, url_for, request
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
from routes.auth_routes import auth_bp  # Import the Blueprint
# from routes.emails_routes import emails_bp

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

app.config.from_object(Config)

# db.init_app(app)  # Initialize db with the app

# Load environment variables from .env file
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# Load the Open AI API secret key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define the scope to access Gmail
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Initialize the SQLAlchemy object
db.init_app(app)

# Register the Blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
# app.register_blueprint(emails_bp, url_prefix="/emails")

# Index route: Checks if the user is authenticated
@app.route("/")
def index():
    if "credentials" not in session:
        return redirect(url_for("auth.authorize"))
    return redirect(url_for("welcome"))

# Define a simple test route to verify database connection
@app.route("/test-connection")
def test_connection():
    try:
        # Use SQLAlchemy's engine to connect and fetch table names
        tables = db.engine.table_names()
        return f"Connected to the database successfully! Available tables: {tables}"
    except Exception as e:
        return f"Failed to connect to the database: {str(e)}"


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
@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
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


def analyze_email_with_openai(email):
    """
    Use OpenAI API to determine if an email contains an actionable task and generate a task description.
    """
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that analyzes emails to identify actionable tasks.",
        },
        {
            "role": "user",
            "content": f"""
            Analyze the following email and determine if it contains an actionable task. If it does, generate a concise task description. Ignore promotional or advertising emails.

            Email Subject: {email.subject}
            From: {email.sender}
            Body: {email.body}

            Respond with either:
            - "Task: " followed by the task description if it's actionable.
            - "Ignore" if it's not actionable.
        """,
        },
    ]

    #response = openai.ChatCompletion.create(
    #    model="gpt-3.5-turbo",
    #    messages=messages,
    #    max_tokens=100,
    #    temperature=0.5,
    #)

    #result = response.choices[0].message["content"].strip()

    #if result.startswith("Task:"):
    #    task_description = result.replace("Task: ", "")

        # Create a new task and add it to the database
    #    new_task = Task(
    #        title=email.subject,
    #        description=task_description,
    #        due_date=None,  # Later: Check and keep track the due date of the task
    #    )

    #    db.session.add(new_task)
    #    db.session.commit()

    #    return new_task


# Run the Flask app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True, port=7000, use_reloader=False)
