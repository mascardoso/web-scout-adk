import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app", "signatures.db")

def show_signatures():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run a website scan first to initialize it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT category, resolved_name, pattern, description FROM signatures ORDER BY category, resolved_name")
    rows = cursor.fetchall()
    conn.close()
    
    print("\n=== Current Web Scout Signature Registry ===")
    print(f"Location: {DB_PATH}\n")
    print(f"{'Category':<12} | {'Resolved Name':<30} | {'Pattern Match':<25} | {'Description'}")
    print("-" * 105)
    
    for row in rows:
        cat, name, pat, desc = row
        # truncate fields for clean terminal display
        desc_str = (desc[:40] + "...") if len(desc) > 40 else desc
        print(f"{cat:<12} | {name:<30} | {pat:<25} | {desc_str}")
        
    print(f"\nTotal registered signatures: {len(rows)}\n")

if __name__ == "__main__":
    show_signatures()
