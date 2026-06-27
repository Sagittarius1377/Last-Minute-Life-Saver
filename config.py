"""
Centralized config loader.
In later phases, this will hold Gemini API key, Firestore credentials path, etc.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env file if present (local dev only — Cloud Run uses real env vars)

# Placeholders — will be used starting Phase 3 (Gemini) and Phase 2 (Firestore)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID", "")