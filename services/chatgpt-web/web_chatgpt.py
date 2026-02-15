import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

app = FastAPI()

# Mount the logs directory
app.mount("/logs", StaticFiles(directory="/app/logs"), name="logs")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key and os.path.exists("key.txt"):
    with open("key.txt") as f:
        api_key = f.read().strip()

client = OpenAI(api_key=api_key)
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"chat_{datetime.now().strftime('%Y-%m-%d')}.log")

def log_interaction(user_msg, reply):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] USER: {user_msg}\n[{ts}] GPT : {reply}\n\n")

@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    user_msg = data.get("message", "")
    if not user_msg:
        return JSONResponse({"error": "Missing message"}, status_code=400)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant on the More Pi dashboard."},
                {"role": "user", "content": user_msg},
            ],
        )
        reply = resp.choices[0].message.content.strip()
        log_interaction(user_msg, reply)
        return {"response": reply}
    except Exception as e:
        err = str(e)
        log_interaction(user_msg, f"ERROR: {err}")
        return JSONResponse({"error": err}, status_code=500)

