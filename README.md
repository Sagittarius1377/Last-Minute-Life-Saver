# ⏰ Last-Minute Life Saver

**AI-Powered Proactive Productivity Companion**
Built for the BlockseBlock Hackathon


 🔗 **Live App:** (https://last-minute-life-saver-b0.streamlit.app/)

---

## Problem

Students, professionals, and entrepreneurs frequently miss deadlines, assignments, meetings, and important commitments because existing productivity tools rely on passive reminders that are easy to ignore. There's a need for an AI-powered companion that proactively helps people plan, prioritize, and actually complete tasks before deadlines are missed — not just remind them.

## Solution

Last-Minute Life Saver goes beyond passive reminders. It uses a large language model to break tasks into actionable steps, actively negotiates trade-offs across a user's entire task list when priorities conflict, learns from each user's real behavior patterns over time, and syncs deadlines into both an in-app calendar and Google Calendar — all behind a simple login so each user's data stays private.

## Key Features

- **🧠 AI Task Breakdown** — breaks any task into 3–5 concrete, actionable steps
- **🤝 Deadline Negotiator** — reasons across the full task list to flag at-risk tasks and recommend what to reschedule, compress, or drop — both automatically when a new task is added and on demand
- **📊 Pattern Memory** — logs every completed/deleted task decision and feeds that history back into the Negotiator, so recommendations get more personalized over time
- **📅 In-App Calendar** — a private, visual month-grid calendar per user, no external account required
- **🔗 Google Calendar Sync** — optional one-click sync of any task to Google Calendar, with automatic ✅ completion updates
- **⏰ Deadline Alerts** — persistent in-app banners for overdue/due-soon tasks, with optional real browser push notifications
- **🔒 Secure Login** — username/password authentication with full data isolation per user

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend / App | Streamlit (Python) |
| AI / LLM | Groq API (Llama 3.3 70B) |
| Database | Google Cloud Firestore |
| Containerization | Docker |
| Deployment | Google Cloud Run |

## Google Technologies Used

- **Google Cloud Firestore** — primary database for tasks, patterns, and user accounts
- **Google Cloud Run** — containerized deployment and hosting
- **Google Cloud Build & Artifact Registry** — CI/CD pipeline for building and storing the Docker image
- **Google Calendar API** — OAuth-based calendar event sync
- **Google Cloud IAM / Service Accounts** — secure backend authentication for Firestore

## Project Structure

```
last-minute-life-saver/
├── app.py                      # Streamlit entry point (UI + routing)
├── config.py                   # Environment variable loading
├── Dockerfile                  # Container build definition
├── requirements.txt            # Python dependencies
├── services/
│   ├── firestore_service.py    # Task CRUD, auth, pattern memory
│   ├── gemini_service.py       # AI task breakdown + Deadline Negotiator (via Groq)
│   └── calendar_service.py     # Google Calendar OAuth + event sync
└── .streamlit/
    └── config.toml             # Theme configuration
```

## Running Locally

```bash
git clone https://github.com/Sagittarius1377/Last-Minute-Life-Saver.git
cd last-minute-life-saver
pip install -r requirements.txt

# Required environment variables (.env):
# GROQ_API_KEY=...
# FIRESTORE_PROJECT_ID=...
# GOOGLE_APPLICATION_CREDENTIALS=firebase-key.json

streamlit run app.py
```

## Deployment

Deployed via Docker to Google Cloud Run:

```bash
gcloud builds submit --tag asia-south1-docker.pkg.dev/PROJECT_ID/life-saver-repo/app:latest

gcloud run deploy last-minute-life-saver \
  --image asia-south1-docker.pkg.dev/PROJECT_ID/life-saver-repo/app:latest \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated
```

## Known Limitations

- **Google Calendar Sync** currently syncs to a single pre-authorized developer Google account for demo purposes, rather than each visitor's own personal calendar. A production version would add per-user OAuth so each user's tasks sync to their own calendar.
- **Deadline alerts** (both in-app banners and browser notifications) only fire while the browser tab is open and active — there's no backend push-notification service, so closed-tab/closed-browser alerts aren't supported in this version.
- **Password hashing** uses SHA-256 without salting, sufficient for demo/testing purposes but not representative of production-grade security practices.

## Built With

Streamlit · Groq (openai/gpt-oss-120b) · Google Cloud Firestore · Google Calendar API · Docker · Google Cloud Run 
