"""
Firestore Service
Phase 2: Task CRUD operations.

NOTE: We don't have user authentication yet, so every task is stored under
a single fixed user ID ("demo_user"). Once we add real auth in a later
phase, this will be replaced with the logged-in user's actual ID.
"""

import os
from datetime import datetime

from google.cloud import firestore
from google.oauth2 import service_account

from config import FIRESTORE_PROJECT_ID

# Path to the service account key, set in .env as GOOGLE_APPLICATION_CREDENTIALS
KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "firebase-key.json")

# Temporary fixed user ID until we add real authentication
DEMO_USER_ID = "demo_user"


def get_db():
    """
    Creates and returns a Firestore client.
    Called fresh each time so Streamlit's rerun model doesn't hold a stale connection.
    """
    credentials = service_account.Credentials.from_service_account_file(KEY_PATH)
    db = firestore.Client(project=FIRESTORE_PROJECT_ID, credentials=credentials)
    return db


def add_task(title: str, deadline: str, priority: str):
    """
    Adds a new task to Firestore under the demo user.
    Returns the new task's auto-generated document ID.
    """
    db = get_db()
    tasks_ref = db.collection("users").document(DEMO_USER_ID).collection("tasks")

    new_task = {
        "title": title,
        "deadline": deadline,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }

    doc_ref = tasks_ref.add(new_task)
    return doc_ref[1].id  # doc_ref is a tuple: (timestamp, DocumentReference)


def get_all_tasks():
    """
    Fetches all tasks for the demo user, ordered by creation time (newest first).
    Returns a list of dicts, each including its Firestore document ID as 'id'.
    """
    db = get_db()
    tasks_ref = db.collection("users").document(DEMO_USER_ID).collection("tasks")

    docs = tasks_ref.order_by("created_at", direction=firestore.Query.DESCENDING).stream()

    tasks = []
    for doc in docs:
        task_data = doc.to_dict()
        task_data["id"] = doc.id
        tasks.append(task_data)

    return tasks


def update_task_status(task_id: str, new_status: str):
    """
    Updates the status of a task (e.g. 'pending' -> 'done').
    """
    db = get_db()
    task_ref = db.collection("users").document(DEMO_USER_ID).collection("tasks").document(task_id)
    task_ref.update({"status": new_status})


def delete_task(task_id: str):
    """
    Deletes a task by its Firestore document ID.
    """
    db = get_db()
    task_ref = db.collection("users").document(DEMO_USER_ID).collection("tasks").document(task_id)
    task_ref.delete()