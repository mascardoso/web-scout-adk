import os
import ssl
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load env variables
load_dotenv()

app = FastAPI(
    title="Web Scout Dashboard",
    description="Local web UI for scanning architectures and previewing drag-and-drop system design canvases."
)

# Setup static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

class ScanRequest(BaseModel):
    url: str
    engine: str  # "groq" or "gemini"

@app.get("/api/debug-version")
def debug_version():
    import hashlib
    agent_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent.py")
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()
        h = hashlib.md5(content.encode("utf-8")).hexdigest()
        lines = content.splitlines()
        return {
            "exists": True,
            "md5": h,
            "size": len(content),
            "first_lines": lines[:15],
            "last_lines": lines[-40:]
        }
    return {"exists": False}

@app.get("/")
def read_root():
    """Serves the main dashboard page."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Dashboard index.html not found. Please create it under app/static/index.html</h1>")

@app.get("/sandbox")
def get_sandbox():
    """Serves the generated architecture sandbox HTML directly over HTTP to bypass iframe file protocol restrictions."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sandbox_path = os.path.join(base_dir, "architecture_sandbox.html")
    if os.path.exists(sandbox_path):
        # We return it with cache disabled so the iframe always reloads fresh scans
        return FileResponse(
            sandbox_path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache"
            }
        )
    # Default placeholder if no scan has run yet
    placeholder_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <style>
    body {
      background-color: #0D111A;
      color: #9CA3AF;
      font-family: 'Outfit', sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      margin: 0;
      overflow: hidden;
    }
    .placeholder-card {
      text-align: center;
      max-width: 320px;
      padding: 2rem;
      border: 1px dashed rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      background: rgba(17, 24, 39, 0.3);
    }
    .placeholder-icon {
      font-size: 2.5rem;
      color: #6366F1;
      margin-bottom: 1rem;
      opacity: 0.65;
    }
    .placeholder-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: #F3F4F6;
      margin-bottom: 0.5rem;
    }
    .placeholder-text {
      font-size: 0.85rem;
      line-height: 1.5;
    }
  </style>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
  <div class="placeholder-card">
    <div class="placeholder-icon">
      <i class="fa-solid fa-diagram-project"></i>
    </div>
    <div class="placeholder-title">No Sandbox Compiled Yet</div>
    <div class="placeholder-text">Enter a target domain in the control console and launch the Web Scout scanner to build your interactive system design canvas.</div>
  </div>
</body>
</html>"""
    return HTMLResponse(placeholder_html)

@app.post("/api/scan")
def run_scout_scan(request: ScanRequest):
    """Executes the autonomous agent workflow based on selected engine."""
    url = request.url.strip()
    engine = request.engine.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="Target URL cannot be empty")
        
    try:
        if engine == "gemini":
            from app.agent import root_agent, scrape_website, get_hosting_details, get_performance_metrics, create_sandbox
            
            # 1. Scrape
            res = scrape_website(url)
            # 2. Geolocation
            h = get_hosting_details(res['ip'])
            # 3. Performance Web Vitals
            p = get_performance_metrics(url)
            # 4. Generate Critique & Sandbox
            sandbox_res = create_sandbox(
                url=res['url'],
                ip=res['ip'],
                server_header=res['server_header'],
                cms=res['cms'],
                db_type=res['database'],
                detected_sdks=res['detected_sdks'],
                hosting_info=h,
                perf_metrics=p,
                detected_techs=res['detected_techs'],
                detected_services=res['detected_services']
            )
            
            # 5. Run LLM critique report
            agent_input = f"Analyze website {url} with signatures {res}, hosting {h}, and metrics {p}."
            critique_response = root_agent.run(agent_input)
            
            return {
                "status": "success",
                "critique": critique_response.text,
                "details": {
                    "cms": res['cms'],
                    "server": res['server_header'],
                    "hosting": f"{h['isp']} ({h['city']}, {h['country']})",
                    "ttfb": f"{p['ttfb']}ms",
                    "lcp": f"{p['lcp']}s",
                    "page_size": f"{p['page_size_mb']} MB"
                }
            }
            
        elif engine == "groq":
            from app.groq_agent import scrape_website_groq, get_hosting_details, get_performance_metrics, compile_sandbox, generate_critique_groq
            from groq import Groq
            
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise HTTPException(status_code=500, detail="GROQ_API_KEY environment variable is not configured on this server instance.")
                
            client = Groq(api_key=api_key)
            
            # Phase 1: Scrape
            res = scrape_website_groq(url, client)
            # Phase 2: Host Geolocation
            h = get_hosting_details(res["ip"])
            # Phase 3: Web Vitals Performance
            p = get_performance_metrics(url)
            
            # Phase 4: Compile static playground
            compile_sandbox(res, h, p)
            
            # Phase 5: Run Critique Llama Audit
            critique = generate_critique_groq(res, h, p, client)
            
            return {
                "status": "success",
                "critique": critique,
                "details": {
                    "cms": res['cms'],
                    "server": res['server_header'],
                    "hosting": f"{h['isp']} ({h['city']}, {h['country']})",
                    "ttfb": f"{p['ttfb']}ms",
                    "lcp": f"{p['lcp']}s",
                    "page_size": f"{p['page_size_mb']} MB"
                }
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported cognitive engine type: {engine}")
            
    except Exception as e:
        # Wrap all exceptions with HTTP 500 error to bubble descriptive logs to interface console
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Groq scan failed: {str(e)}")

# Mount static files (this handles js, css inside app/static)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    # Bind to standard port 8080
    uvicorn.run("web_server:app", host="0.0.0.0", port=8080, reload=True)
