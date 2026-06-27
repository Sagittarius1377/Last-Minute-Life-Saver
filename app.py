"""
Last-Minute Life Saver
Phase 2: Real task storage via Firestore (CRUD wired in)
"""

import streamlit as st
from services.firestore_service import add_task, get_all_tasks, update_task_status, delete_task

# --- Page setup ---
st.set_page_config(
    page_title="Last-Minute Life Saver",
    page_icon="⏰",
    layout="wide"
)

# --- Sidebar ---
st.sidebar.title("⏰ Last-Minute Life Saver")
st.sidebar.write("AI-powered productivity companion")
st.sidebar.markdown("---")
st.sidebar.success("Phase 2: Firestore connected ✅")

# --- Main page ---
st.title("Last-Minute Life Saver")
st.write("Your AI productivity companion that helps you actually finish things, not just remind you about them.")

st.markdown("---")

# --- Task list (now pulled live from Firestore) ---
st.subheader("📋 Your Tasks")

try:
    tasks = get_all_tasks()
except Exception as e:
    st.error(f"Could not connect to Firestore: {e}")
    tasks = []

if not tasks:
    st.info("No tasks yet. Add one below to get started.")
else:
    for task in tasks:
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
        with col1:
            label = task["title"]
            if task.get("status") == "done":
                label = f"~~{label}~~"
            st.write(f"**{label}**")
        with col2:
            st.write(task.get("deadline", "—"))
        with col3:
            st.write(task.get("priority", "—"))
        with col4:
            if task.get("status") != "done":
                if st.button("✅ Done", key=f"done_{task['id']}"):
                    update_task_status(task["id"], "done")
                    st.rerun()
        with col5:
            if st.button("🗑️", key=f"delete_{task['id']}"):
                delete_task(task["id"])
                st.rerun()

st.markdown("---")

# --- Add new task form ---
st.subheader("➕ Add a new task")
with st.form("new_task_form", clear_on_submit=True):
    new_title = st.text_input("Task title")
    new_deadline = st.text_input("Deadline (e.g. 2026-06-28 18:00)")
    new_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    submitted = st.form_submit_button("Add Task")

    if submitted:
        if not new_title.strip():
            st.warning("Please enter a task title.")
        else:
            add_task(new_title.strip(), new_deadline.strip(), new_priority)
            st.success(f"Task '{new_title}' added!")
            st.rerun()