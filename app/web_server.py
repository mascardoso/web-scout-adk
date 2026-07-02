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
    return HTMLResponse("<h3>No sandbox has been compiled yet. Run a scan from the control panel!</h3>")

@app.post("/api/scan")
def run_scan(request: ScanRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")
        
    engine = request.engine.lower()
    
    # 1. Groq Engine (Zero-Rate-Limit)
    if engine == "groq":
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(status_code=400, detail="GROQ_API_KEY is not set in your .env file.")
            
        try:
            client = Groq(api_key=api_key)
            from app.groq_agent import scrape_website_groq, get_hosting_details, get_performance_metrics, compile_sandbox, generate_critique_groq
            
            res = scrape_website_groq(url, client)
            h = get_hosting_details(res["ip"])
            p = get_performance_metrics(url)
            compile_sandbox(res, h, p)
            critique = generate_critique_groq(res, h, p, client)
            
            return {
                "status": "success",
                "critique": critique,
                "details": {
                    "cms": res["cms"],
                    "server": res["server_header"],
                    "hosting": f"{h['isp']} ({h['city']}, {h['country']})",
                    "ttfb": f"{p['ttfb']}ms",
                    "lcp": f"{p['lcp']}s",
                    "page_size": f"{p['page_size_mb']} MB"
                }
            }
        except Exception as e:
            # Handle rate limits gracefully
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                return {
                    "status": "rate_limited",
                    "message": "Groq free-tier rate limit reached. Restarts shortly or plug in a paid key.",
                    "critique": "### Rate Limit Exceeded\nPlease wait a minute or set up billing."
                }
            raise HTTPException(status_code=500, detail=f"Groq scan failed: {e}")
            
    # 2. Gemini Engine (ADK Pipeline)
    elif engine == "gemini":
        try:
            from app.agent import scrape_website, get_hosting_details, get_performance_metrics, create_sandbox
            
            # Execute Gemini pipeline locally bypassing the planning framework for safety
            res = scrape_website(url)
            h = get_hosting_details(res["ip"])
            p = get_performance_metrics(url)
            create_sandbox(
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
            
            # Since Gemini key might be rate-limited, we can write a simple fallback critique or call Gemini
            from google import genai
            from google.genai import types
            
            client = genai.Client()
            prompt = f"Write a simple system design critique for {url} based on CMS: {res['cms']}, Web Vitals: TTFB {p['ttfb']}ms, LCP {p['lcp']}s. Keep it short."
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-pro',
                    contents=prompt
                )
                critique = response.text
            except Exception:
                critique = f"### Architecture Critique: {url}\n*   **CMS Core:** {res['cms']}\n*   **Server Header:** {res['server_header']}\n*   **Performance:** TTFB {p['ttfb']}ms, LCP {p['lcp']}s.\n\n*(Note: Detailed Gemini critique generation bypassed due to active API rate-limits)*"
                
            return {
                "status": "success",
                "critique": critique,
                "details": {
                    "cms": res["cms"],
                    "server": res["server_header"],
                    "hosting": f"{h['isp']} ({h['city']}, {h['country']})",
                    "ttfb": f"{p['ttfb']}ms",
                    "lcp": f"{p['lcp']}s",
                    "page_size": f"{p['page_size_mb']} MB"
                }
            }
        except Exception as e:
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                return {
                    "status": "rate_limited",
                    "message": "Gemini API free-tier daily rate limit (20 calls) reached. Restarts tomorrow at 9:00 AM Lisbon time.",
                    "critique": "### Gemini Quota Exceeded\nYour Gemini Developer API key has reached its 20-request daily limit. Please use the Groq engine option or wait for the quota to reset."
                }
            raise HTTPException(status_code=500, detail=f"Gemini scan failed: {e}")
            
    else:
        raise HTTPException(status_code=400, detail="Invalid engine selected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
