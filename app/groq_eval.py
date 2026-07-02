import os
import sys
import json
import time
from groq import Groq

# Add root folder to python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Groq agent tools
from app.groq_agent import scrape_website_groq, get_hosting_details, get_performance_metrics, compile_sandbox

# Eval cases definition
EVAL_CASES = [
    {
        "id": "case_1_monolith",
        "url": "jornalviarapida.com",
        "expected_cms": "WordPress",
        "description": "Tests monolithic WordPress signature matching and database placement."
    },
    {
        "id": "case_2_microservices",
        "url": "app.lokalise.com",
        "expected_cms": "PHP",
        "description": "Tests SaaS SPA microservice architecture lane dynamic compilation."
    }
]

def run_judge(client: Groq, url: str, scan_res: dict, critique: str) -> dict:
    """Uses Llama-3.3-70b as a judge to evaluate the agent output quality."""
    prompt = f"""You are an independent AI Systems Evaluation Judge. 
    Evaluate the quality of a System Design Scout agent's output for target site: {url}
    
    Scan Results: {json.dumps(scan_res, indent=2)}
    Agent Critique:
    ---
    {critique}
    ---
    
    Grade the agent on two criteria (1 to 5 scale, where 5 is perfect):
    1. Task Success: Did the agent successfully extract technical components (CMS, hosting, vitals) and compile them?
    2. Critique Quality: Is the critique professional, highly tailored to a frontend engineer, and free of generic filler?
    
    Respond ONLY with a valid JSON object matching this schema:
    {{
        "task_success_score": <int>,
        "critique_quality_score": <int>,
        "task_success_reason": "<explanation>",
        "critique_quality_reason": "<explanation>"
    }}
    """
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {
            "task_success_score": 1,
            "critique_quality_score": 1,
            "task_success_reason": f"Judge error: {e}",
            "critique_quality_reason": ""
        }

def run_evaluation():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("[!] Error: GROQ_API_KEY is not set.")
        sys.exit(1)
        
    client = Groq(api_key=api_key)
    print("="*60)
    print("🚀 STARTING STANDALONE GROQ AGENT EVALUATION RUN")
    print("="*60 + "\n")
    
    results = []
    
    for case in EVAL_CASES:
        url = case["url"]
        print(f"[*] Running Case: {case['id']} ({url})...")
        start_time = time.time()
        
        # 1. Scrape
        res = scrape_website_groq(url, client)
        
        # 2. Host Geolocation
        h = get_hosting_details(res["ip"])
        
        # 3. Performance Metrics
        p = get_performance_metrics(url)
        
        # 4. Compile Sandbox HTML
        sandbox_url = compile_sandbox(res, h, p)
        
        # 5. Generate Critique
        from app.groq_agent import generate_critique_groq
        critique = generate_critique_groq(res, h, p, client)
        
        elapsed = time.time() - start_time
        print(f"    Completed in {elapsed:.2f}s. Running Judge...")
        
        # 6. Judge output
        grades = run_judge(client, url, res, critique)
        
        results.append({
            "case_id": case["id"],
            "url": url,
            "expected_cms": case["expected_cms"],
            "actual_cms": res["cms"],
            "sandbox_path": sandbox_url,
            "task_success": grades["task_success_score"],
            "task_success_reason": grades["task_success_reason"],
            "critique_quality": grades["critique_quality_score"],
            "critique_quality_reason": grades["critique_quality_reason"]
        })
        print(f"    [GRADED] Task Success: {grades['task_success_score']}/5 | Critique Quality: {grades['critique_quality_score']}/5\n")
        
    # Output final summary table
    print("\n" + "="*60)
    print("📊 EVALUATION SUMMARY TABLE")
    print("="*60)
    print(f"{'Case ID':<20} | {'Domain':<20} | {'CMS Match':<10} | {'Success':<8} | {'Quality':<8}")
    print("-"*75)
    for r in results:
        cms_ok = "✅" if r["expected_cms"] in r["actual_cms"] else "❌"
        print(f"{r['case_id']:<20} | {r['url']:<20} | {cms_ok} ({r['actual_cms'][:8]}) | {r['task_success']}/5     | {r['critique_quality']}/5")
    print("="*60)
    
    # Write report file
    report_file = "artifacts/groq_eval_report.json"
    os.makedirs("artifacts", exist_ok=True)
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[REPORT SAVED] Detailed evaluation report saved to: file://{os.path.abspath(report_file)}\n")

if __name__ == "__main__":
    run_evaluation()
