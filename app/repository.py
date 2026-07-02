import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "signatures.db")

class SignatureRepository:
    def __init__(self):
        self.db_path = DB_PATH
        self.initialize_db()

    def initialize_db(self):
        """Creates the signatures table and seeds initial default patterns if empty."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signatures (
                pattern TEXT PRIMARY KEY,
                category TEXT,
                resolved_name TEXT,
                description TEXT
            )
        """)
        
        # Check if table is empty
        cursor.execute("SELECT COUNT(*) FROM signatures")
        if cursor.fetchone()[0] == 0:
            # Seed initial signatures (defaults from our hardcoded list)
            initial_seeds = [
                # CMS
                ("wp-content", "cms", "WordPress (PHP)", "Popular open-source Content Management System running PHP."),
                ("wp-includes", "cms", "WordPress (PHP)", "Popular open-source Content Management System running PHP."),
                
                # SDKs
                ("googletagmanager.com", "sdk", "Google Analytics/GTM", "Tag management system for running analytics and marketing scripts."),
                ("google-analytics.com", "sdk", "Google Analytics/GTM", "Web analytics service tracking pageviews and conversions."),
                ("connect.facebook.net", "sdk", "Meta Pixel", "Conversion tracking pixel for social ad optimization."),
                ("googlesyndication.com", "sdk", "Google AdSense", "Advertising network SDK for display ads."),
                ("pagead2", "sdk", "Google AdSense", "Advertising network SDK for display ads."),
                ("static.hotjar.com", "sdk", "Hotjar", "User behavior recording and heatmap analytics platform."),
                ("intercom", "sdk", "Intercom Chat Widget", "Live chat support widget and messaging platform."),
                ("onetrust", "sdk", "OneTrust Consent SDK", "Cookie consent management compliance banner."),
                ("ot-sdk", "sdk", "OneTrust Consent SDK", "Cookie consent management compliance banner."),
                
                # Techs
                ("jquery", "tech", "jQuery", "Fast, small, and feature-rich JavaScript utility library."),
                ("elementor", "tech", "Elementor Page Builder", "Visual drag-and-drop page editor for WordPress layouts."),
                ("tailwind", "tech", "Tailwind CSS", "Utility-first CSS framework for modern user interface styling."),
                ("bootstrap", "tech", "Bootstrap", "Popular CSS framework for responsive layout components."),
                ("yoast", "tech", "Yoast SEO", "Search engine optimization planning module."),
                ("fontawesome", "tech", "FontAwesome", "Vector icon and social logo stylesheet collection."),
                ("font-awesome", "tech", "FontAwesome", "Vector icon and social logo stylesheet collection."),
                ("webcomponents", "tech", "Web Components", "Native browser web components loader for custom UI tags."),
                ("login-page", "tech", "Custom Elements (<login-page>)", "HTML5 Custom Element tag mounting dynamic components."),
                
                # Services / Endpoints
                ("identity", "service", "Identity Service API", "Decoupled backend service handling authentication and user profile states."),
                ("maestro", "service", "Maestro Cloud API", "Task scheduling and backend cloud orchestration gateway."),
                ("socket.io", "service", "WebSockets Gateway", "Real-time bi-directional network socket channel for live updates."),
                ("nextgen", "service", "NextGen App Server", "Separate modern app frame rendering server.")
            ]
            cursor.executemany("INSERT INTO signatures VALUES (?, ?, ?, ?)", initial_seeds)
            conn.commit()
            
        conn.close()

    def get_all(self):
        """Returns all registered signatures as a list of dicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM signatures")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def save_signature(self, pattern, category, resolved_name, description=""):
        """Inserts or updates a signature in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO signatures (pattern, category, resolved_name, description)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(pattern) DO UPDATE SET
                category=excluded.category,
                resolved_name=excluded.resolved_name,
                description=coalesce(nullif(excluded.description, ''), signatures.description)
        """, (pattern, category, resolved_name, description))
        conn.commit()
        conn.close()

    def match_signatures(self, html_content: str):
        """Scans the HTML against all stored signatures and returns categorized results.
        
        Returns:
            dict: { 'cms': str, 'detected_sdks': list, 'detected_techs': list, 'detected_services': list }
        """
        html_lower = html_content.lower()
        signatures = self.get_all()
        
        cms = "Unknown"
        detected_sdks = []
        detected_techs = []
        detected_services = []
        
        for sig in signatures:
            pattern = sig["pattern"].lower()
            if pattern in html_lower:
                category = sig["category"]
                name = sig["resolved_name"]
                
                if category == "cms":
                    cms = name
                elif category == "sdk":
                    if name not in detected_sdks:
                        detected_sdks.append(name)
                elif category == "tech":
                    if name not in detected_techs:
                        detected_techs.append(name)
                elif category == "service":
                    if name not in detected_services:
                        detected_services.append(name)
                        
        return {
            "cms": cms,
            "detected_sdks": detected_sdks,
            "detected_techs": detected_techs,
            "detected_services": detected_services
        }
