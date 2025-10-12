from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import psutil, socket, time, secrets, jwt, datetime

SECRET = "morepi-secret-key"   # store securely or via env var
ALGORITHM = "HS256"
CLIENT_ID = "chatgpt-desktop"
REDIRECT_URI = "http://localhost:8081/oauth/callback"  # ChatGPT will override
TOKENS = {}

app = FastAPI(title="MorePi MCP Agent (OAuth)")

def create_token():
    payload = {
        "sub": "localuser",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

# === OAuth endpoints ===
@app.get("/authorize")
def authorize(response_type: str, client_id: str, redirect_uri: str, state: str):
    if client_id != CLIENT_ID:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    # Auto-approve (no login screen)
    token = create_token()
    code = secrets.token_hex(8)
    TOKENS[code] = token
    return RedirectResponse(f"{redirect_uri}?code={code}&state={state}")

@app.post("/token")
async def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...)
):
    if code not in TOKENS:
        raise HTTPException(status_code=400, detail="Invalid code")
    token = TOKENS.pop(code)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 1800
    }

# === Middleware to enforce Bearer token ===
@app.middleware("http")
async def verify_auth(request: Request, call_next):
    if request.url.path.startswith("/authorize") or request.url.path.startswith("/token") or request.url.path == "/schema":
        return await call_next(request)
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        jwt.decode(auth.split()[1], SECRET, algorithms=[ALGORITHM])
    except Exception:
        return JSONResponse({"error": "Invalid or expired token"}, status_code=401)
    return await call_next(request)

# === Normal endpoints ===
@app.get("/schema")
def schema():
    return {
        "name": "MorePi MCP Agent",
        "version": "1.0",
        "auth": {"type": "oauth", "client_id": CLIENT_ID},
        "endpoints": {
            "/info": "Get system information",
            "/disk": "Get disk usage stats"
        }
    }

@app.get("/info")
def info():
    return {
        "hostname": socket.gethostname(),
        "cpu_percent": psutil.cpu_percent(),
        "mem_percent": psutil.virtual_memory().percent,
        "uptime_seconds": time.time() - psutil.boot_time()
    }

@app.get("/disk")
def disk():
    usage = psutil.disk_usage('/')
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "percent_used": usage.percent
    }

