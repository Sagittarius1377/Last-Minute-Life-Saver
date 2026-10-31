"""
AI Service (Phase 3 + 4)
Originally built on Gemini, now running on Groq's API instead, due to
Gemini's free-tier quota being unreliable (limit: 0 errors affecting many
developers as of mid-2026). Groq uses an OpenAI-compatible API and has a
generous, stable free tier.

Function names (breakdown_task, negotiate_deadlines) are kept identical
to the original Gemini version so app.py needs no changes.
"""

from groq import Groq
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

# Llama 3.3 70B is fast and capable, good fit for this use case
MODEL_NAME = "openai/gpt-oss-120b"


def _call_groq(prompt: str) -> str:
    """
    Shared helper: sends a prompt to Groq's chat completion endpoint
    and returns the plain text response.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def breakdown_task(title: str, deadline: str, priority: str) -> str:
    """
    Breaks a task down into 3-5 short, concrete, actionable steps.
    Returns plain text (a numbered list) to display in the UI.
    """
    prompt = f"""
You are a productivity assistant helping a student or professional who is at risk of missing a deadline.

Task: {title}
Deadline: {deadline if deadline else "not specified"}
Priority: {priority}

Break this task down into 3-5 short, concrete, actionable steps the person can start doing right now.
Keep each step under 12 words. Do not add any preamble or explanation — just output a numbered list.
"""
    return _call_groq(prompt)


def negotiate_deadlines(tasks: list, new_task: dict = None, patterns: list = None) -> str:
    """
    Looks at the user's full task list (and optionally a newly-added task)
    and reasons about trade-offs: what's at risk, what should be reprioritized,
    rescheduled, or dropped, and why.

    `tasks` is a list of dicts with keys: title, deadline, priority, status.
    `new_task` (optional) is the task that was just added.
    `patterns` (optional) is a list of recent user decisions (Phase 5: Pattern Memory),
    used to personalize the recommendation based on the user's actual habits.

    Returns plain text reasoning + recommendations to display in the UI.
    """
    pending_tasks = [t for t in tasks if t.get("status") != "done"]

    if not pending_tasks:
        return "No pending tasks to negotiate — you're all caught up!"

    task_list_text = "\n".join(
        f"- {t['title']} | deadline: {t.get('deadline') or 'not specified'} | priority: {t.get('priority', 'Medium')}"
        for t in pending_tasks
    )

    trigger_context = ""
    if new_task:
        trigger_context = f"""
The user just added a new task:
- {new_task['title']} | deadline: {new_task.get('deadline') or 'not specified'} | priority: {new_task.get('priority', 'Medium')}

Focus your reasoning especially on how this new task affects the rest of the schedule.
"""

    pattern_context = ""
    if patterns:
        pattern_lines = "\n".join(
            f"- {p['decision_type']} '{p['task_title']}' (priority: {p.get('task_priority', 'Medium')})"
            for p in patterns
        )
        pattern_context = f"""
Here is the user's recent task history (what they actually did, not just what they planned):
{pattern_lines}

Use this history to personalize your advice — e.g. if they tend to delay or drop certain kinds
of tasks, factor that into your recommendation instead of giving generic advice.
"""

    prompt = f"""
You are a "Deadline Negotiator" — an AI productivity assistant. The user has the following pending tasks:

{task_list_text}

{trigger_context}

{pattern_context}

Reason briefly about trade-offs between these tasks: which are at real risk of being missed,
which could be rescheduled, compressed, or dropped, and why — based on deadline urgency and priority.

Then give a short, clear recommendation (2-4 sentences max). Be direct and practical, like a
sharp friend helping someone triage their week — not generic advice. Do not just restate the task list.
"""
    return _call_groq(prompt)