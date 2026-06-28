"""
Firestore Service
Phase 2 (updated): Task CRUD operations, now properly multi-user.

Every function takes a `user_id` so each visitor's tasks, patterns, and
calendar links are kept fully separate in Firestore. In app.py, this
user_id comes from a per-browser-session ID generated on first visit
(no login required) — see get_session_user_id() in app.py.
"""

import os
import hashlib
from datetime import datetime

from google.cloud import firestore
from google.oauth2 import service_account

from config import FIRESTORE_PROJECT_ID

# Path to the service account key, set in .env as GOOGLE_APPLICATION_CREDENTIALS
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "firebase-key.json")


def get_db():
    """
    Creates and returns a Firestore client.
    Called fresh each time so Streamlit's rerun model doesn't hold a stale connection.
    """
    credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
    db = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)
    return db


def add_task(user_id: str, title: str, deadline: str, priority: str):
    """
    Adds a new task to Firestore under this specific user.
    Returns the new task's auto-generated document ID.
    """
    db = get_db()
    tasks_ref = db.collection("users").document(user_id).collection("tasks")

    new_task = {
        "title": title,
        "deadline": deadline,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    doc_ref = tasks_ref.add(new_task)
    return doc_ref[1].id  # doc_ref is a tuple: (timestamp, DocumentReference)


def get_all_tasks(user_id: str):
    """
    Fetches all tasks for this specific user, ordered by creation time (newest first).
    Returns a list of dicts, each including its Firestore document ID as 'id'.
    """
    db = get_db()
    tasks_ref = db.collection("users").document(user_id).collection("tasks")

    docs = tasks_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()

    tasks = []
    for doc in docs:
        task_data = doc.to_dict()
        task_data["id"] = doc.id
        tasks.append(task_data)

    return tasks


def update_task_status(user_id: str, task_id: str, new_status: str):
    """
    Updates the status of a task (e.g. 'pending' -> 'done').
    """
    db = get_db()
    task_ref = db.collection("users").document(user_id).collection("tasks").document(task_id)
    task_ref.update({"status": new_status})


def save_calendar_event_id(user_id: str, task_id: str, event_id: str):
    """
    Stores the Google Calendar event ID on a task, so that marking the
    task 'done' later can also update the corresponding calendar event.
    """
    db = get_db()
    task_ref = db.collection("users").document(user_id).collection("tasks").document(task_id)
    task_ref.update({"calendar_event_id": event_id})


def delete_task(user_id: str, task_id: str):
    """
    Deletes a task by its Firestore document ID.
    """
    db = get_db()
    task_ref = db.collection("users").document(user_id).collection("tasks").document(task_id)
    task_ref.delete()


def log_pattern(user_id: str, decision_type: str, task_title: str, task_priority: str, task_deadline: str):
    """
    Logs a user decision (e.g. 'completed', 'deleted') for pattern memory.
    This builds a history of how the user actually handles tasks over time,
    which gets fed back into the Deadline Negotiator as context.
    """
    db = get_db()
    patterns_ref = db.collection("users").document(user_id).collection("patterns")

    patterns_ref.add({
        "decision_type": decision_type,
        "task_title": task_title,
        "task_priority": task_priority,
        "task_deadline": task_deadline,
        "timestamp": datetime.utcnow().isoformat(),
    })


def get_recent_patterns(user_id: str, limit: int = 10):
    """
    Fetches the most recent user decisions, newest first.
    Used to give the Deadline Negotiator context on the user's real habits.
    """
    db = get_db()
    patterns_ref = db.collection("users").document(user_id).collection("patterns")

    docs = patterns_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()

    return [doc.to_dict() for doc in docs]


def hash_password(password):
    """Simple SHA-256 password hashing for basic hackathon security."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_or_register(username, password):
    """
    Checks if a user exists. 
    If yes: verifies password.
    If no: automatically registers them and sets up their vault.
    Returns (user_id, message, is_success)
    """
    # FIXED HERE: Changed get_db_client() to get_db() to match your existing helper
    db = get_db()
    user_ref = db.collection("users").document(username.lower().strip())
    user_doc = user_ref.get()
    
    hashed = hash_password(password)
    
    if user_doc.exists:
        stored_data = user_doc.to_dict()
        if stored_data.get("password") == hashed:
            return username.lower().strip(), "Welcome back!", True
        else:
            return None, "Incorrect password for this username.", False
    else:
        # User doesn't exist, auto-create account for frictionless hackathon testing
        user_ref.set({
            "username": username.lower().strip(),
            "password": hashed,
            "created_at": datetime.now().isoformat()
        })
        return username.lower().strip(), "Account created successfully!", True