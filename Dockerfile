# --- Base image ---
FROM python:3.11-slim

# --- Set working directory ---
WORKDIR /app

# --- Install system dependencies (kept minimal for now) ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- Copy requirements first (better Docker layer caching) ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copy the rest of the app ---
COPY . .

# --- Cloud Run expects the app to listen on $PORT (defaults to 8080) ---
ENV PORT=8080
EXPOSE 8080

# --- Run Streamlit ---
# address 0.0.0.0 is required so Cloud Run can reach the container
CMD streamlit run app.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false