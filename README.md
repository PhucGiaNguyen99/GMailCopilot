# GmailCopilot (Backend)

**GmailCopilot** is a smart backend service that connects to a user’s Gmail account, scans incoming emails in real-time, and uses rule-based logic and basic NLP to classify them. It automatically extracts actionable items from emails and creates a personal to-do list, helping users stay on top of important messages in a cluttered inbox.

## Features
- Secure Gmail integration with OAuth 2.0
- Real-time scheduled email fetching from Gmail API
- Email classification using rule-based NLP:
  - `task`: Actionable emails (e.g., deadlines, requests)
  - `info`: Informational (e.g., receipts, confirmations)
  - `promo`: Promotional/marketing content
- Automatic task creation from actionable emails
- RESFUL API endpoints to manage tasks and classified emails
- PostgreSQL database for persistent task storage

## Tech Stack

| Layer            | Technology              |
|------------------|--------------------------|
| Backend Framework| Flask                    |
| API Design       | Flask-RESTful / Flask Blueprints |
| Email Access     | Gmail API + OAuth 2.0    |
| NLP              | Python (spaCy, regex)    |
| Database         | SQLite (dev) / PostgreSQL (prod) |
| Background Tasks | APScheduler              |
| Auth             | Google OAuth 2.0         |

---
## Project Structure
gmailcopilot/
├── app/
│ ├── init.py
│ ├── routes/
│ │ └── email_routes.py
│ ├── services/
│ │ └── gmail_service.py
│ │ └── classification_service.py
│ ├── models/
│ │ └── task.py
│ │ └── email.py
│ └── utils/
│ └── nlp_utils.py
├── config.py
├── run.py
├── requirements.txt
└── README.md

## Planned Endpoints

| Method | Endpoint        | Description                            |
|--------|------------------|----------------------------------------|
| GET    | `/tasks`         | Retrieve all extracted tasks           |
| POST   | `/scan`          | Trigger Gmail scan and classification  |
| GET    | `/emails`        | Retrieve all processed emails          |
| GET    | `/emails?type=task` | Filter emails by classification     |
| PUT    | `/tasks/<id>`    | Update task status                     |
| DELETE | `/tasks/<id>`    | Delete a task                          |

---
## Email Classification Logic

Emails are classified into:
- **`task`**: Contains action verbs and dates (e.g., “Submit report by Friday”)
- **`info`**: Includes receipts, confirmations, order updates
- **`promo`**: Promotional offers, newsletters, marketing content

Classification is performed using:
- Rule-based keyword matching
- Basic NLP with `spaCy` and regex

---

## To-Do Status (Backend Progress)

- [x] Setup Gmail API authentication (OAuth 2.0)
- [x] Fetch emails using Gmail API
- [x] Strip HTML and extract clean body content
- [x] Build classification logic (task/info/promo)
- [x] Extract and save tasks from task-related emails
- [x] Design and build REST API for emails and tasks
- [ ] Schedule email scanning (APScheduler)
- [ ] Add unit tests for core services

---

## Installation & Setup

```bash
git clone https://github.com/yourusername/gmailcopilot.git
cd gmailcopilot

# Set up virtual environment
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set up Gmail API credentials
# Place credentials.json in the root directory

# Run the Flask app
python run.py
