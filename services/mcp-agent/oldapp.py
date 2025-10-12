from fastapi import FastAPI
import psutil
import socket

app = FastAPI(title="MCP Agent for ChatGPT")

@app.get("/schema")
def schema():
    return {
        "name": "MorePi MCP Agent",
        "version": "1.0",
        "description": "Provides system and container status to ChatGPT",
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
        "uptime_seconds": psutil.boot_time()
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

