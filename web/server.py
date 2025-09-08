
import asyncio
import json
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
from info import Config
from bot.database.connection_manager import get_database
from clone_manager import clone_manager

app = Flask(__name__)
app.secret_key = Config.WEBHOOK_SECRET or "default_secret_key"

# HTML Templates
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Storage Builder Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; margin-top: 5px; }
        .clones-section { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .clone-item { padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: between; align-items: center; }
        .clone-status { padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; }
        .status-running { background-color: #28a745; }
        .status-stopped { background-color: #dc3545; }
        .status-pending { background-color: #ffc107; color: #000; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin: 2px; }
        .btn-primary { background-color: #007bff; color: white; }
        .btn-danger { background-color: #dc3545; color: white; }
        .btn-warning { background-color: #ffc107; color: black; }
        .refresh-btn { float: right; }
        .log-section { background: #1e1e1e; color: #00ff00; padding: 15px; border-radius: 8px; max-height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 12px; }
        .system-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .info-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    <script>
        function refreshDashboard() {
            location.reload();
        }
        
        function manageClone(botId, action) {
            fetch(`/api/clone/${botId}/${action}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) refreshDashboard();
                })
                .catch(error => alert('Error: ' + error));
        }
        
        // Auto-refresh every 30 seconds
        setInterval(refreshDashboard, 30000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Storage Builder Dashboard</h1>
            <p>Real-time monitoring and management</p>
            <button class="btn btn-primary refresh-btn" onclick="refreshDashboard()">🔄 Refresh</button>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_clones }}</div>
                <div class="stat-label">Total Clones</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.running_clones }}</div>
                <div class="stat-label">Running Clones</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_users }}</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_files }}</div>
                <div class="stat-label">Stored Files</div>
            </div>
        </div>
        
        <div class="clones-section">
            <h2>🤖 Clone Management</h2>
            {% for clone in clones %}
            <div class="clone-item">
                <div>
                    <strong>{{ clone.name or clone.id }}</strong>
                    <br>
                    <small>Owner: {{ clone.owner_id }} | Created: {{ clone.created_at.strftime('%Y-%m-%d %H:%M') if clone.created_at else 'Unknown' }}</small>
                </div>
                <div>
                    <span class="clone-status status-{{ clone.status }}">{{ clone.status.upper() }}</span>
                    {% if clone.status == 'running' %}
                        <button class="btn btn-warning" onclick="manageClone('{{ clone.id }}', 'restart')">🔄 Restart</button>
                        <button class="btn btn-danger" onclick="manageClone('{{ clone.id }}', 'stop')">⏹️ Stop</button>
                    {% else %}
                        <button class="btn btn-primary" onclick="manageClone('{{ clone.id }}', 'start')">▶️ Start</button>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="system-info">
            <div class="info-card">
                <h3>💾 Storage Information</h3>
                <p><strong>Total Files:</strong> {{ storage_stats.total_files }}</p>
                <p><strong>Storage Used:</strong> {{ storage_stats.total_size_mb }} MB</p>
                <p><strong>Storage Path:</strong> {{ storage_stats.storage_path }}</p>
            </div>
            
            <div class="info-card">
                <h3>🖥️ System Health</h3>
                <p><strong>Database:</strong> <span style="color: {{ 'green' if system_health.database else 'red' }}">{{ '✅ Connected' if system_health.database else '❌ Disconnected' }}</span></p>
                <p><strong>Uptime:</strong> {{ system_health.uptime }}</p>
                <p><strong>Last Updated:</strong> {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}</p>
            </div>
        </div>
        
        <div class="log-section" style="margin-top: 20px;">
            <h3>📋 Recent Activity</h3>
            <div id="logs">
                {% for log in recent_logs %}
                <div>[{{ log.timestamp }}] {{ log.message }}</div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Storage Builder - Login</title>
    <style>
        body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .login-form { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .form-group { margin-bottom: 20px; }
        input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <form class="login-form" method="post">
        <h2>🔐 Dashboard Login</h2>
        <div class="form-group">
            <input type="password" name="password" placeholder="Admin Password" required>
        </div>
        <button type="submit" class="btn">Login</button>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </form>
</body>
</html>
"""

# Dashboard data collection functions
async def get_dashboard_stats():
    """Collect dashboard statistics"""
    try:
        db = get_database()
        if not db:
            return {}
        
        # Get clone statistics
        total_clones = await db.clones.count_documents({})
        running_clones = len(clone_manager.get_running_clones())
        
        # Get user statistics
        total_users = await db.users.count_documents({})
        
        # Get file statistics
        total_files = await db.files.count_documents({}) if 'files' in await db.list_collection_names() else 0
        
        return {
            'total_clones': total_clones,
            'running_clones': running_clones,
            'total_users': total_users,
            'total_files': total_files
        }
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        return {}

async def get_clones_data():
    """Get clones data for dashboard"""
    try:
        db = get_database()
        if not db:
            return []
        
        clones_cursor = db.clones.find().sort("created_at", -1)
        clones = await clones_cursor.to_list(None)
        
        # Enhance with runtime status
        running_clones = clone_manager.get_running_clones()
        
        for clone in clones:
            clone['status'] = 'running' if clone['_id'] in running_clones else clone.get('status', 'stopped')
            clone['id'] = clone['_id']
        
        return clones
    except Exception as e:
        print(f"Error getting clones data: {e}")
        return []

async def get_storage_stats():
    """Get storage statistics"""
    try:
        from bot.utils.file_manager import file_manager
        return await file_manager.get_storage_stats()
    except Exception as e:
        print(f"Error getting storage stats: {e}")
        return {}

async def get_system_health():
    """Get system health information"""
    try:
        db = get_database()
        database_connected = db is not None
        
        # Calculate uptime (simplified)
        uptime = "Running"  # You can implement actual uptime calculation
        
        return {
            'database': database_connected,
            'uptime': uptime
        }
    except Exception as e:
        print(f"Error getting system health: {e}")
        return {}

async def get_recent_logs():
    """Get recent logs for dashboard"""
    try:
        db = get_database()
        if not db:
            return []
        
        logs_cursor = db.logs.find().sort("timestamp", -1).limit(10)
        logs = await logs_cursor.to_list(10)
        
        return [
            {
                'timestamp': log['timestamp'].strftime('%H:%M:%S'),
                'message': log['message']
            }
            for log in logs
        ]
    except Exception as e:
        print(f"Error getting recent logs: {e}")
        return []

# Flask routes
@app.route('/')
def dashboard():
    """Main dashboard route"""
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    
    # Run async functions in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        stats = loop.run_until_complete(get_dashboard_stats())
        clones = loop.run_until_complete(get_clones_data())
        storage_stats = loop.run_until_complete(get_storage_stats())
        system_health = loop.run_until_complete(get_system_health())
        recent_logs = loop.run_until_complete(get_recent_logs())
        
        return render_template_string(
            DASHBOARD_TEMPLATE,
            stats=stats,
            clones=clones,
            storage_stats=storage_stats,
            system_health=system_health,
            recent_logs=recent_logs,
            datetime=datetime
        )
    finally:
        loop.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if request.method == 'POST':
        password = request.form.get('password')
        # Simple password check (in production, use proper authentication)
        if password == Config.WEBHOOK_SECRET or password == "admin123":
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid password")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/api/clone/<bot_id>/<action>', methods=['POST'])
def manage_clone(bot_id, action):
    """API endpoint for clone management"""
    if not session.get('authenticated'):
        return jsonify({'success': False, 'message': 'Authentication required'})
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        if action == 'start':
            success, message = loop.run_until_complete(clone_manager.start_clone(bot_id))
        elif action == 'stop':
            success, message = loop.run_until_complete(clone_manager.stop_clone(bot_id))
        elif action == 'restart':
            success, message = loop.run_until_complete(clone_manager.restart_clone(bot_id))
        else:
            return jsonify({'success': False, 'message': 'Invalid action'})
        
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        loop.close()

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Authentication required'})
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        stats = loop.run_until_complete(get_dashboard_stats())
        return jsonify(stats)
    finally:
        loop.close()

def start_webserver():
    """Start the web server in a separate thread"""
    def run_server():
        try:
            app.run(
                host=Config.WEB_HOST,
                port=Config.WEB_PORT,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            print(f"Web server error: {e}")
    
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread
