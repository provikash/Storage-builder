from flask import Flask, jsonify, render_template_string
import asyncio
from datetime import datetime
import threading

app = Flask(__name__)

# HTML template for the monitoring dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Mother Bot System Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-healthy { color: #28a745; }
        .status-degraded { color: #ffc107; }
        .status-critical { color: #dc3545; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .metric { display: flex; justify-content: space-between; margin: 10px 0; }
        h1, h2 { color: #333; }
        .refresh-note { text-align: center; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Mother Bot System Dashboard</h1>
        <p class="refresh-note">Auto-refreshes every 30 seconds</p>

        <div class="grid">
            <div class="card">
                <h2>System Health</h2>
                <div class="metric">
                    <span>Status:</span>
                    <span class="status-{{ health_status }}">{{ health_status|title }}</span>
                </div>
                <div class="metric">
                    <span>Last Check:</span>
                    <span>{{ last_health_check }}</span>
                </div>
            </div>

            <div class="card">
                <h2>Clone Statistics</h2>
                <div class="metric">
                    <span>Total Clones:</span>
                    <span>{{ clone_stats.total }}</span>
                </div>
                <div class="metric">
                    <span>Active Clones:</span>
                    <span>{{ clone_stats.active }}</span>
                </div>
                <div class="metric">
                    <span>Running Now:</span>
                    <span>{{ running_clones }}</span>
                </div>
                <div class="metric">
                    <span>Pending Requests:</span>
                    <span>{{ clone_stats.pending }}</span>
                </div>
            </div>

            <div class="card">
                <h2>Subscription Stats</h2>
                <div class="metric">
                    <span>Total Subscriptions:</span>
                    <span>{{ sub_stats.total }}</span>
                </div>
                <div class="metric">
                    <span>Active:</span>
                    <span>{{ sub_stats.active }}</span>
                </div>
                <div class="metric">
                    <span>Expired:</span>
                    <span>{{ sub_stats.expired }}</span>
                </div>
                <div class="metric">
                    <span>Total Revenue:</span>
                    <span>${{ "%.2f"|format(sub_stats.total_revenue) }}</span>
                </div>
            </div>

            <div class="card">
                <h2>System Resources</h2>
                <div class="metric">
                    <span>Memory Usage:</span>
                    <span>{{ "%.1f"|format(system_stats.memory_percent) }}%</span>
                </div>
                <div class="metric">
                    <span>CPU Usage:</span>
                    <span>{{ "%.1f"|format(system_stats.cpu_percent) }}%</span>
                </div>
                <div class="metric">
                    <span>Uptime:</span>
                    <span>{{ "%.1f"|format(system_stats.uptime_seconds/3600) }} hours</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Recent Activity</h2>
            <p>Last updated: {{ current_time }}</p>
            <p>Dashboard URL: <code>/dashboard</code></p>
            <p>API Health: <code>/health</code></p>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return jsonify({
        "status": "Mother Bot System API",
        "endpoints": {
            "/health": "System health check",
            "/dashboard": "Web dashboard",
            "/api/stats": "System statistics"
        }
    })

@app.route('/health')
def health():
    try:
        # Import here to avoid circular imports
        from bot.utils.health_check import health_checker
        from bot.utils.system_monitor import system_monitor
        from clone_manager import clone_manager

        health_status = health_checker.get_status()
        system_stats = system_monitor.get_stats()

        return jsonify({
            "status": "ok",
            "health": health_status,
            "system": system_stats,
            "running_clones": len(clone_manager.get_running_clones()),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/dashboard')
def dashboard():
    try:
        # Import here to avoid circular imports
        from bot.utils.health_check import health_checker
        from bot.utils.system_monitor import system_monitor
        from clone_manager import clone_manager
        from bot.database.clone_db import get_clone_statistics
        from bot.database.subscription_db import get_subscription_stats

        # Get current stats (simplified for demo)
        health_status = health_checker.status or "unknown"
        last_health_check = health_checker.last_check or "Never"

        # Mock stats (replace with actual async calls in production)
        clone_stats = {"total": 0, "active": 0, "pending": 0}
        sub_stats = {"total": 0, "active": 0, "expired": 0, "total_revenue": 0}
        system_stats = system_monitor.get_stats()

        return render_template_string(DASHBOARD_HTML,
            health_status=health_status,
            last_health_check=last_health_check,
            clone_stats=clone_stats,
            sub_stats=sub_stats,
            system_stats=system_stats,
            running_clones=len(clone_manager.get_running_clones()),
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    except Exception as e:
        return f"Dashboard Error: {e}", 500

@app.route('/api/stats')
def api_stats():
    try:
        from clone_manager import clone_manager
        return jsonify({
            "running_clones": len(clone_manager.get_running_clones()),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_server():
    """Run the web monitoring dashboard"""
    from flask import Flask, jsonify, render_template_string
    import threading

    app = Flask(__name__)

    @app.route('/dashboard')
    def dashboard():
        try:
            from clone_manager import clone_manager
            running_clones = len(clone_manager.get_running_clones())

            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Mother Bot Dashboard</title></head>
            <body>
                <h1>🤖 Mother Bot Dashboard</h1>
                <div>
                    <h2>System Status</h2>
                    <p>Running Clones: {{ clones }}</p>
                    <p>Status: ✅ Operational</p>
                </div>
            </body>
            </html>
            """
            return render_template_string(html, clones=running_clones)
        except Exception as e:
            return f"Dashboard Error: {str(e)}", 500

    @app.route('/health')
    def health():
        try:
            from clone_manager import clone_manager
            return jsonify({
                "status": "ok",
                "health": "healthy",
                "running_clones": len(clone_manager.get_running_clones()),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/api/status')
    def api_status():
        try:
            from clone_manager import clone_manager
            return jsonify({
                "status": "operational",
                "running_clones": len(clone_manager.get_running_clones()),
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    try:
        # Try port 5000 first, then fall back to 8080
        try:
            app.run(host='0.0.0.0', port=5000, debug=False)
        except OSError as port_error:
            if "Address already in use" in str(port_error):
                print("Port 5000 in use, trying port 8080...")
                app.run(host='0.0.0.0', port=8080, debug=False)
            else:
                raise port_error
    except Exception as e:
        print(f"Web server error: {e}")

def start_webserver():
    """Start web server in background thread"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))  # Use 8080 if 5000 is in use
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Port {port} in use, trying port {port + 1}")
            app.run(host='0.0.0.0', port=port + 1, debug=False)