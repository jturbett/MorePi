#!/usr/bin/env python3
import os, time, json, ssl, websocket, urllib3
urllib3.disable_warnings()

NVR = os.getenv("NVR_URL", "https://192.168.1.59")
API_TOKEN = os.getenv("API_TOKEN", "").strip()
OUTPUT_FILE = "/var/www/html/unifi_events.json"
DEBUG_FILE = "/var/www/html/unifi_debug.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(DEBUG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

log(f"🔌 Starting UniFi Protect WebSocket collector for {NVR}")

if not API_TOKEN:
    log("❌ ERROR: API_TOKEN is not set. Exiting.")
    raise SystemExit(1)

ws_url = NVR.replace("https", "wss") + "/proxy/protect/integration/v1/ws"
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, dict) and data.get("type") in ["motion", "smartDetectZone", "connect", "disconnect"]:
            log(f"🎥 Event: {data.get('type')} from {data.get('cameraName')}")
            try:
                with open(OUTPUT_FILE, "r") as f:
                    events = json.load(f)
            except Exception:
                events = []
            events.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "camera": data.get("cameraName", "unknown"),
                "type": data.get("type")
            })
            events = events[-50:]
            with open(OUTPUT_FILE, "w") as f:
                json.dump(events, f, indent=2)
    except Exception as e:
        log(f"⚠️ Error parsing message: {e} | Raw: {message[:100]}")

def on_error(ws, error):
    log(f"❌ WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    log(f"🔌 WebSocket closed ({close_status_code}) {close_msg}")

def on_open(ws):
    log("✅ WebSocket connected to UniFi Protect")

