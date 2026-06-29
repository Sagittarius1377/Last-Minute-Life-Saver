"""
Last-Minute Life Saver
Phase 7 (updated): Real username/password login (auto-registers new users
for frictionless hackathon testing) + in-app calendar view + reliable
in-app deadline alerts via st.toast.
"""

import uuid
import calendar as cal_module
import datetime as dt

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from services import firestore_service
from services.firestore_service import add_task, get_all_tasks, update_task_status, delete_task, log_pattern, get_recent_patterns, save_calendar_event_id
from services.gemini_service import breakdown_task, negotiate_deadlines
from services.calendar_service import push_task_to_calendar, get_upcoming_events, mark_event_completed

st.set_page_config(page_title="Last-Minute Life Saver", page_icon="⏰", layout="wide")

# --- AUTHENTICATION STATE INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# --- AUTHENTICATION GATE UI ---
if not st.session_state.authenticated:
    st.title("🚨 Last-Minute Life Saver")
    st.subheader("Your AI-Powered Proactive Productivity Companion")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("""
        ### Welcome to your intelligent workspace.
        This companion actively monitors your deadlines, negotiates adjustments via AI,
        and prevents missed commitments.

        *💡 **Note for Judges:** Enter any unique username and password. If the account
        doesn't exist, it will be automatically created instantly for your testing session.*
        """)

    with col2:
        st.write("### 🔒 Secure Dashboard Access")
        username_input = st.text_input("Username", placeholder="e.g., harry").strip()
        password_input = st.text_input("Password", type="password", placeholder="••••••••")

        if st.button("Access My Companion Dashboard", use_container_width=True):
            if username_input and password_input:
                user_id, msg, success = firestore_service.authenticate_or_register(username_input, password_input)
                if success:
                    st.session_state.user_id = user_id
                    st.session_state.authenticated = True
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Please fill out both username and password fields.")
    st.stop()  # Halts app execution here so unauthenticated users cannot see the dashboard

# --- LIVE AUTHENTICATED DASHBOARD ---
# Everything below this line only executes if st.session_state.authenticated is True
USER_ID = st.session_state.user_id

# Reruns the script every 20 seconds via Streamlit's own internal mechanism
# (not a real page reload), so deadline alerts get rechecked automatically
# without ever touching/resetting st.session_state — login stays intact.
st_autorefresh(interval=20000, key="deadline_check_refresh")

with st.sidebar:
    st.write(f"👤 **Logged in as:** `{USER_ID}`")
    if st.button("Log Out"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.rerun()

# --- Priority styling helpers ---
PRIORITY_COLORS = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}


def priority_badge(priority: str) -> str:
    icon = PRIORITY_COLORS.get(priority, "⚪")
    return f"{icon} {priority}"


# --- Load tasks once up front (used by sidebar stats + main list) ---
try:
    tasks = get_all_tasks(USER_ID)
    firestore_error = None
except Exception as e:
    tasks = []
    firestore_error = str(e)

pending_count = sum(1 for t in tasks if t.get("status") != "done")
done_count = sum(1 for t in tasks if t.get("status") == "done")
high_priority_pending = sum(1 for t in tasks if t.get("status") != "done" and t.get("priority") == "High")


def render_deadline_alerts(task_list):
    """
    Shows a persistent, hard-to-miss banner inside the app for overdue or
    soon-due tasks — using st.error/st.warning instead of st.toast, since
    toast messages auto-vanish after a few seconds and are easy to miss.

    These banners are also re-shown on every rerun while the condition is
    still true (overdue stays overdue), so they won't disappear just
    because the page refreshed.

    Limitation (stated honestly): this only updates when the app reruns —
    either from your own clicks, or from the auto-refresh added via the
    <meta refresh> tag above. It can't wake up a fully closed browser tab;
    that needs a push-notification backend, a different architecture.
    """
    # Use explicit IST time for comparisons — never rely on the server's
    # system clock. Cloud Run containers run on UTC by default, while
    # deadlines are always entered in IST, so comparing against a naive
    # dt.datetime.now() would be silently off by 5.5 hours in production.
    from zoneinfo import ZoneInfo
    now = dt.datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
    overdue_tasks = []
    due_soon_tasks = []

    for t in task_list:
        if t.get("status") == "done":
            continue
        deadline = t.get("deadline", "")
        if not deadline:
            continue

        try:
            if len(deadline) == 10:
                deadline_dt = dt.datetime.strptime(deadline, "%Y-%m-%d")
            else:
                deadline_dt = dt.datetime.strptime(deadline, "%Y-%m-%d %H:%M")
        except ValueError:
            continue

        if deadline_dt <= now:
            overdue_tasks.append(t["title"])
        elif deadline_dt - now <= dt.timedelta(hours=1):
            due_soon_tasks.append(t["title"])

    if overdue_tasks:
        st.error(f"⏰ **Overdue:** {', '.join(overdue_tasks)}")
    if due_soon_tasks:
        st.warning(f"⚠️ **Due within the hour:** {', '.join(due_soon_tasks)}")


def render_browser_notifications(task_list):
    """
    Bonus layer alongside render_deadline_alerts: a real OS-level browser
    popup notification, in addition to the in-app banner (which is the
    reliable one — this one depends on browser permissions and may not
    always fire due to platform restrictions on notifications inside
    Streamlit's sandboxed component iframe).

    Requires a real click on the "Enable Deadline Alerts" button (browsers
    block permission prompts that aren't triggered by an actual user
    gesture). Once granted, fires an immediate confirmation notification.
    """
    import json

    notify_data = []
    for t in task_list:
        if t.get("status") == "done":
            continue
        deadline = t.get("deadline", "")
        if not deadline:
            continue
        if len(deadline) == 10:
            iso_deadline = deadline + "T00:00:00"
        else:
            iso_deadline = deadline.replace(" ", "T") + ":00"
        notify_data.append({"id": t["id"], "title": t["title"], "deadline": iso_deadline})

    js_data = json.dumps(notify_data)

    components.html(f"""
    <div id="notif-status" style="font-family: sans-serif; font-size: 14px;"></div>
    <button id="enable-notif-btn" style="
        background-color: #ff4b4b; color: white; border: none;
        padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px;
    ">🔔 Enable Deadline Alerts</button>

    <script>
    (function() {{
        const tasks = {js_data};
        const statusEl = document.getElementById("notif-status");
        const btn = document.getElementById("enable-notif-btn");

        if (!("Notification" in window)) {{
            statusEl.innerText = "This browser doesn't support notifications.";
            btn.style.display = "none";
            return;
        }}

        function scheduleNotifications() {{
            const now = new Date().getTime();
            tasks.forEach(function(task) {{
                const deadlineTime = new Date(task.deadline).getTime();
                const diffMs = deadlineTime - now;
                const notifiedKey = "notified_" + task.id;

                if (diffMs <= 0) {{
                    if (!sessionStorage.getItem(notifiedKey)) {{
                        new Notification("⏰ Overdue: " + task.title, {{
                            body: "This task's deadline has passed."
                        }});
                        sessionStorage.setItem(notifiedKey, "1");
                    }}
                }} else if (diffMs <= 24 * 60 * 60 * 1000) {{
                    setTimeout(function() {{
                        new Notification("⏰ Due now: " + task.title, {{
                            body: "This task's deadline is here."
                        }});
                        sessionStorage.setItem(notifiedKey, "1");
                    }}, diffMs);
                }}
            }});
        }}

        function updateUI() {{
            if (Notification.permission === "granted") {{
                statusEl.innerText = "✅ Browser alerts are on.";
                btn.style.display = "none";
                scheduleNotifications();
            }} else if (Notification.permission === "denied") {{
                statusEl.innerText = "🔕 Notifications blocked — enable them in your browser's site settings.";
                btn.style.display = "none";
            }} else {{
                btn.style.display = "inline-block";
            }}
        }}

        btn.addEventListener("click", function() {{
            Notification.requestPermission().then(function(permission) {{
                if (permission === "granted") {{
                    new Notification("🎉 Browser alerts enabled!", {{
                        body: "You'll get a popup when task deadlines hit, as long as this tab stays open."
                    }});
                }}
                updateUI();
            }});
        }});

        updateUI();
    }})();
    </script>
    """, height=70)


def render_month_calendar(task_list, year, month):
    """
    Renders a real visual month-grid calendar (no Google account needed),
    showing this user's own task deadlines on the correct days.
    """
    days_with_tasks = {}
    for t in task_list:
        deadline = t.get("deadline", "")
        if not deadline:
            continue
        try:
            task_date = dt.datetime.strptime(deadline[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if task_date.year == year and task_date.month == month:
            days_with_tasks.setdefault(task_date.day, []).append({
                "title": t["title"],
                "done": t.get("status") == "done",
            })

    cal = cal_module.Calendar(firstweekday=6)  # Sunday-first
    weeks = cal.monthdayscalendar(year, month)

    today = dt.date.today()

    html = f"""
    <div style="font-family: sans-serif;">
        <table style="width: 100%; border-collapse: collapse; table-layout: fixed;">
            <tr>
    """
    for day_name in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
        html += f'<th style="padding: 6px; font-size: 12px; color: #888; text-align: center;">{day_name}</th>'
    html += "</tr>"

    for week in weeks:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += '<td style="padding: 6px; vertical-align: top;"></td>'
                continue

            is_today = (day == today.day and month == today.month and year == today.year)
            cell_style = "padding: 6px; vertical-align: top; border: 1px solid #eee; min-height: 60px;"
            if is_today:
                cell_style += " background-color: #fff3cd;"

            day_tasks = days_with_tasks.get(day, [])
            task_html = ""

            def task_line(dt_task):
                color = "#999" if dt_task["done"] else "#d9534f"
                strike = "text-decoration: line-through;" if dt_task["done"] else ""
                return f'<div style="font-size: 11px; color: {color}; {strike} white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">• {dt_task["title"]}</div>'

            if len(day_tasks) <= 3:
                for dt_task in day_tasks:
                    task_html += task_line(dt_task)
            else:
                # First 3 always visible; the rest are revealed by clicking
                # "+N more" — uses a native HTML <details> element, which
                # natively supports click-to-expand with zero JavaScript.
                for dt_task in day_tasks[:3]:
                    task_html += task_line(dt_task)
                remaining_html = "".join(task_line(t) for t in day_tasks[3:])
                task_html += f'''
                <details style="font-size: 10px; color: #aaa; cursor: pointer;">
                    <summary style="cursor: pointer;">+{len(day_tasks) - 3} more</summary>
                    {remaining_html}
                </details>
                '''

            html += f'<td style="{cell_style}"><div style="font-size: 12px; font-weight: bold;">{day}</div>{task_html}</td>'
        html += "</tr>"

    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)


render_deadline_alerts(tasks)
render_browser_notifications(tasks)

# --- Sidebar (continued) ---
with st.sidebar:
    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Pending", pending_count)
    with col_b:
        st.metric("Completed", done_count)

    if high_priority_pending > 0:
        st.warning(f"⚠️ {high_priority_pending} high-priority task(s) still pending")
    elif pending_count == 0 and done_count > 0:
        st.success("🎉 All caught up!")

    st.markdown("---")
    st.caption("🔔 In-app alerts are on — keep this tab open to get notified when deadlines hit.")
    st.caption("Built for the BlockseBlock Hackathon")

# --- Main page header ---
st.title("⏰ Last-Minute Life Saver")
st.write("Your AI productivity companion that helps you actually finish things, not just remind you about them.")
st.markdown("---")

# Show success message from a previous action (carried across st.rerun())
if "task_added_message" in st.session_state:
    st.success(st.session_state["task_added_message"])
    del st.session_state["task_added_message"]

# --- Tabs: Task list vs. My Calendar ---
tab_tasks, tab_calendar = st.tabs(["📋 Your Tasks", "📅 My Calendar"])

with tab_calendar:
    st.caption("This calendar is private to your account — no Google account needed.")
    today = dt.date.today()
    col_prev, col_label, col_next = st.columns([1, 3, 1])
    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
        st.session_state["cal_month"] = today.month
    with col_prev:
        if st.button("◀ Prev"):
            st.session_state["cal_month"] -= 1
            if st.session_state["cal_month"] == 0:
                st.session_state["cal_month"] = 12
                st.session_state["cal_year"] -= 1
    with col_label:
        st.markdown(
            f"<h4 style='text-align: center; margin: 0;'>{cal_module.month_name[st.session_state['cal_month']]} {st.session_state['cal_year']}</h4>",
            unsafe_allow_html=True
        )
    with col_next:
        if st.button("Next ▶"):
            st.session_state["cal_month"] += 1
            if st.session_state["cal_month"] == 13:
                st.session_state["cal_month"] = 1
                st.session_state["cal_year"] += 1

    render_month_calendar(tasks, st.session_state["cal_year"], st.session_state["cal_month"])

with tab_tasks:
    if firestore_error:
        st.error(f"Could not connect to Firestore: {firestore_error}")

    if not tasks:
        st.info("No tasks yet. Add one below to get started.")
    else:
        for task in tasks:
            is_done = task.get("status") == "done"

            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([4, 2, 1.3, 2])

                with col1:
                    label = task["title"]
                    if is_done:
                        st.markdown(f"~~**{label}**~~")
                    else:
                        st.markdown(f"**{label}**")

                with col2:
                    st.write(f"📆 {task.get('deadline') or 'No deadline'}")

                with col3:
                    st.write(priority_badge(task.get("priority", "Medium")))

                with col4:
                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        if not is_done:
                            if st.button("✅", key=f"done_{task['id']}", help="Mark as done", use_container_width=True):
                                update_task_status(USER_ID, task["id"], "done")
                                log_pattern(USER_ID, "completed", task["title"], task.get("priority", "Medium"), task.get("deadline", ""))
                                event_id = task.get("calendar_event_id")
                                if event_id:
                                    try:
                                        mark_event_completed(event_id)
                                    except Exception:
                                        pass
                                st.rerun()
                    with action_col2:
                        with st.popover("⋮", use_container_width=True):
                            if st.button("🧠 Break it down", key=f"breakdown_{task['id']}", use_container_width=True):
                                with st.spinner("Thinking..."):
                                    steps = breakdown_task(task["title"], task.get("deadline", ""), task.get("priority", ""))
                                st.session_state[f"steps_{task['id']}"] = steps
                                st.rerun()

                            if task.get("deadline"):
                                if st.button("📅 Sync to Google Calendar", key=f"calendar_{task['id']}", use_container_width=True, help="Optional — syncs to the developer's personal Google Calendar for demo purposes"):
                                    with st.spinner("Syncing to calendar..."):
                                        try:
                                            result = push_task_to_calendar(task["title"], task.get("deadline", ""))
                                            save_calendar_event_id(USER_ID, task["id"], result["event_id"])
                                            st.session_state[f"calendar_link_{task['id']}"] = result["link"]
                                        except Exception as e:
                                            st.session_state[f"calendar_error_{task['id']}"] = str(e)
                                    st.rerun()
                            else:
                                st.caption("📅 Set a deadline to sync to Calendar")

                            if st.button("🗑️ Delete", key=f"delete_{task['id']}", use_container_width=True):
                                log_pattern(USER_ID, "deleted", task["title"], task.get("priority", "Medium"), task.get("deadline", ""))
                                delete_task(USER_ID, task["id"])
                                st.rerun()

                if f"steps_{task['id']}" in st.session_state:
                    st.info(st.session_state[f"steps_{task['id']}"])

                cal_link_key = f"calendar_link_{task['id']}"
                cal_error_key = f"calendar_error_{task['id']}"
                if cal_link_key in st.session_state:
                    st.success(f"Synced to Google Calendar (demo account)! [View event]({st.session_state[cal_link_key]})")
                if cal_error_key in st.session_state:
                    st.error(f"Calendar sync failed: {st.session_state[cal_error_key]}")

        st.markdown("")
        if st.button("🤝 Negotiate My Schedule", type="primary"):
            with st.spinner("Negotiating..."):
                recent_patterns = get_recent_patterns(USER_ID, limit=10)
                result = negotiate_deadlines(tasks, patterns=recent_patterns)
            st.session_state["negotiation_result"] = result
            st.rerun()

        if "negotiation_result" in st.session_state:
            st.markdown("##### 🤝 Negotiator's Take")
            st.warning(st.session_state["negotiation_result"])

st.markdown("---")

# --- Add new task form ---
st.subheader("➕ Add a new task")
with st.form("new_task_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([3, 1.5, 1.2, 1.3])
    with col1:
        new_title = st.text_input("Task title")
    with col2:
        new_date = st.date_input("Deadline date (optional)", value=None, min_value=dt.date.today())
    with col3:
        new_time = st.text_input("Time (optional, 24-hr)", placeholder="e.g. 17:00 for 5 PM")
    with col4:
        new_priority = st.selectbox("Priority", ["High", "Medium", "Low"])

    submitted = st.form_submit_button("Add Task", type="primary")

    if submitted:
        if not new_title.strip():
            st.warning("Please enter a task title.")
        else:
            deadline_str = ""

            if new_date and new_time.strip():
                try:
                    parsed_time = dt.datetime.strptime(new_time.strip(), "%H:%M").time()
                    candidate_deadline = dt.datetime.combine(new_date, parsed_time)

                    from zoneinfo import ZoneInfo
                    now_ist = dt.datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)

                    if candidate_deadline <= now_ist:
                        st.error("That time has already passed today. Please choose a future time. Task saved with date only.")
                        deadline_str = new_date.strftime('%Y-%m-%d')
                    else:
                        deadline_str = f"{new_date.strftime('%Y-%m-%d')} {parsed_time.strftime('%H:%M')}"
                except ValueError:
                    st.error("Time must be in 24-hour HH:MM format, e.g. 17:00 for 5 PM. Task saved with date only.")
                    deadline_str = new_date.strftime('%Y-%m-%d')
            elif new_date:
                deadline_str = new_date.strftime('%Y-%m-%d')
            elif new_time.strip():
                st.warning("You entered a time but no date — please also pick a date. Task saved with no deadline for now.")

            add_task(USER_ID, new_title.strip(), deadline_str, new_priority)

            new_task_dict = {
                "title": new_title.strip(),
                "deadline": deadline_str,
                "priority": new_priority,
                "status": "pending",
            }
            with st.spinner("Checking how this affects your schedule..."):
                existing_tasks = get_all_tasks(USER_ID)
                if not any(t["title"] == new_task_dict["title"] for t in existing_tasks):
                    existing_tasks.append(new_task_dict)
                recent_patterns = get_recent_patterns(USER_ID, limit=10)
                st.session_state["negotiation_result"] = negotiate_deadlines(
                    existing_tasks, new_task=new_task_dict, patterns=recent_patterns
                )

            st.session_state["task_added_message"] = f"Task '{new_title}' added!"
            st.rerun()