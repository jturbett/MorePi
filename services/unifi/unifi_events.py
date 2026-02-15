#!/usr/bin/env python3
import os, time, json, requests

NVR = os.getenv("NVR_URL", "https://192.168.1.59").rstrip("/")
API_TOKEN = os.getenv("API_TOKEN", "").strip()

OUT = "/var/www/html/unifi_events.json"
DBG = "/var/www/html/unifi_debug.log"

os.makedirs(os.path.dirname(OUT), exist_ok=True)

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(DBG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

if not API_TOKEN:
    log("❌ ERROR: API_TOKEN is not set. Exiting.")
    raise SystemExit(1)

S = requests.Session()
S.verify = False  # UniFi uses self-signed cert
S.headers.update({"Authorization": f"Bearer {API_TOKEN}", "User-Agent": "unifi-collector/REST-1.0"})

MAX_EVENTS = 200

def load_events():
    try:
        with open(OUT, "r") as f:
            return json.load(f)
    except Exception:
        return []

def save_events(evts):
    try:
        with open(OUT, "w") as f:
            json.dump(evts[-MAX_EVENTS:], f, indent=2)
    except Exception as e:
        log(f"⚠️ write error: {e}")

def norm(ev):
    cam = (
        ev.get("cameraName")
        or (ev.get("camera") or {}).get("name")
        or ev.get("source")
        or "unknown"
    )
    etype = ev.get("type") or ev.get("event") or "unknown"
    ts_ms = ev.get("end") or ev.get("start") or ev.get("ts") or int(time.time()*1000)
    return {
        "ts": int(ts_ms/1000),
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ts_ms/1000))),
        "type": etype,
        "camera": cam,
        "id": ev.get("id") or f"{etype}:{cam}:{ts_ms}",
    }

def poll_loop():
    end_ms = int(time.time()) * 1000
    since_ms = end_ms - 30*60*1000  # last 30 minutes

    cache = load_events()
    seen = {e.get("id") for e in cache if isinstance(e, dict) and e.get("id")}
    save_events(cache)  # ensure file exists

    log("ℹ️ REST polling started (/proxy/protect/api/events every 5s)")
    while True:
        try:
            url = f"{NVR}/proxy/protect/api/events?limit=200&start={since_ms}&end={end_ms}"
            r = S.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                items = data.get("items") if isinstance(data, dict) else data
                if items:
                    new_evts = []
                    for raw in items:
                        try:
                            e = norm(raw if isinstance(raw, dict) else {})
                            if e["id"] not in seen:
                                seen.add(e["id"])
                                new_evts.append(e)
                        except Exception:
                            continue
                    if new_evts:
                        cache.extend(sorted(new_evts, key=lambda x: x["ts"]))
                        cache = cache[-MAX_EVENTS:]
                        save_events(cache)
                        log(f"🗂️ Added {len(new_evts)} events (total {len(cache)})")
                # slide the window forward
                end_ms = int(time.time()) * 1000
                since_ms = end_ms - 30*60*1000
            else:
                log(f"⚠️ REST {r.status_code}: {r.text[:120]}")
        except Exception as e:
            log(f"⚠️ REST error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    poll_loop()

