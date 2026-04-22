from flask import Flask, render_template_string, jsonify, request, session
import os
import sqlite3
import json
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "world_builder_99")

# --- DATABASE SETUP ---
DB_PATH = 'cities.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS players 
            (user_id TEXT PRIMARY KEY, money INTEGER, xp INTEGER, level INTEGER, grid TEXT)''')

init_db()

GRID_SIZE = 25
BUILDING_CONFIG = {
    "road": {"cost": 20, "xp": 5, "min_level": 1, "income": 0, "color": "#475569", "icon": "🛣️", "requires_road": False},
    "house": {"cost": 150, "xp": 30, "min_level": 1, "income": 15, "color": "#10b981", "icon": "🏠", "requires_road": True},
    "park": {"cost": 100, "xp": 50, "min_level": 1, "income": 2, "color": "#4ade80", "icon": "🌳", "requires_road": False},
    "police": {"cost": 600, "xp": 120, "min_level": 2, "income": 10, "color": "#3b82f6", "icon": "👮", "requires_road": True},
    "fire_dept": {"cost": 750, "xp": 150, "min_level": 2, "income": 10, "color": "#ef4444", "icon": "🚒", "requires_road": True},
    "factory": {"cost": 1500, "xp": 250, "min_level": 3, "income": 80, "color": "#94a3b8", "icon": "🏭", "requires_road": True},
    "hospital": {"cost": 1200, "xp": 300, "min_level": 3, "income": 40, "color": "#f59e0b", "icon": "🏥", "requires_road": True},
    "mall": {"cost": 5000, "xp": 1000, "min_level": 5, "income": 350, "color": "#fb7185", "icon": "🛍️", "requires_road": True}
}

# --- DB HELPERS ---
def get_player(uid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM players WHERE user_id = ?", (uid,)).fetchone()
        if user:
            data = dict(user)
            data['grid'] = json.loads(data['grid'])
            return data
    return None

def save_player(uid, data):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("REPLACE INTO players (user_id, money, xp, level, grid) VALUES (?, ?, ?, ?, ?)",
            (uid, data['money'], data['xp'], data['level'], json.dumps(data['grid'])))

# --- ROUTES ---
@app.before_request
def ensure_user():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    if not get_player(session['user_id']):
        new_city = {"money": 2500, "xp": 0, "level": 1, "grid": ["empty"] * (GRID_SIZE**2)}
        save_player(session['user_id'], new_city)

@app.route('/')
def index():
    return render_template_string(open(__file__).read().split("'''html")[1].split("html'''")[0], config=BUILDING_CONFIG)

@app.route('/api/state')
def get_state():
    p = get_player(session['user_id'])
    # Simulate income based on time since last check (Simplified for Cloud)
    return jsonify(p)

@app.route('/api/build', methods=['POST'])
def build():
    p = get_player(session['user_id'])
    b_type, idx = request.json.get('type'), request.json.get('index')
    conf = BUILDING_CONFIG.get(b_type)

    if not conf or p['grid'][idx] != "empty" or p['money'] < conf['cost']:
        return jsonify({"error": "Failed"}), 400

    if conf.get("requires_road"):
        neighbors = [idx-25, idx+25, idx-1, idx+1]
        if not any(0 <= n < 625 and p['grid'][n] == "road" for n in neighbors):
            return jsonify({"error": "Needs a Road!"}), 400

    p['money'] -= conf['cost']
    p['grid'][idx] = b_type
    p['xp'] += conf['xp']
    p['level'] = (p['xp'] // 600) + 1
    save_player(session['user_id'], p)
    return jsonify({"success": True})

@app.route('/api/remove', methods=['POST'])
def remove():
    p = get_player(session['user_id'])
    p['grid'][request.json.get('index')] = "empty"
    save_player(session['user_id'], p)
    return jsonify({"success": True})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8160))
    app.run(host='0.0.0.0', port=port)

'''html
<!DOCTYPE html>
<html>
<head>
    <title>Global Metropolis</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --accent: #38bdf8; --bg: #0f172a; --panel: #1e293b; }
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: white; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 320px; background: var(--panel); border-right: 2px solid #334155; padding: 20px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; }
        .stat-box { background: var(--bg); padding: 12px; border-radius: 8px; border: 1px solid #334155; }
        .stat-box div { color: var(--accent); font-weight: 800; font-size: 1.1rem; }
        .tool-card { background: #334155; padding: 10px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 12px; border: 2px solid transparent; }
        .tool-card.selected { border-color: var(--accent); background: #0f172a; }
        .viewport { flex-grow: 1; overflow: auto; background-color: #020617; padding: 50px; }
        .grid-container { display: grid; grid-template-columns: repeat(25, 50px); gap: 2px; background: #334155; padding: 10px; border-radius: 8px; width: fit-content; }
        .tile { width: 50px; height: 50px; background: #1e293b; display: flex; justify-content: center; align-items: center; font-size: 1.5rem; cursor: crosshair; }
        .tile:hover { outline: 2px solid var(--accent); background: #ffffff11; }
        .road-tile { background: #334155 !important; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2 style="margin:0; color:var(--accent);">🏙️ Global City</h2>
        <div class="stat-box"><small>MONEY</small><div id="money">$0</div></div>
        <div class="stat-box"><small>PROGRESS</small><div id="stats">Lvl 1</div></div>
        <div id="tools-list" style="display:flex; flex-direction:column; gap:6px;"></div>
        <div class="tool-card" style="color:#ef4444; border-color:#ef4444;" onclick="selectTool('remove')"><span>🚜</span><b>BULLDOZER</b></div>
    </div>
    <div class="viewport"><div class="grid-container" id="map"></div></div>
    <script>
        const config = {{ config|tojson }};
        let selectedTool = null;
        async function update() {
            const res = await fetch('/api/state');
            const data = await res.json();
            document.getElementById('money').innerText = '$' + data.money.toLocaleString();
            document.getElementById('stats').innerText = `Lvl ${data.level} - ${data.xp} XP`;
            const toolsList = document.getElementById('tools-list');
            if(toolsList.children.length === 0) {
                Object.keys(config).forEach(id => {
                    const div = document.createElement('div');
                    div.id = 'tool-' + id;
                    div.className = 'tool-card';
                    div.onclick = () => { selectedTool = id; update(); };
                    div.innerHTML = `<span>${config[id].icon}</span><div><b>${id.toUpperCase()}</b><br><small>$${config[id].cost}</small></div>`;
                    toolsList.appendChild(div);
                });
            }
            Object.keys(config).forEach(id => {
                document.getElementById('tool-' + id).className = `tool-card ${data.level < config[id].min_level ? 'locked' : ''} ${selectedTool === id ? 'selected' : ''}`;
            });
            const map = document.getElementById('map');
            if (map.children.length === 0) {
                for(let i=0; i < 625; i++) {
                    const tile = document.createElement('div');
                    tile.className = 'tile'; tile.id = 'tile-' + i;
                    tile.onclick = async () => {
                        await fetch(selectedTool === 'remove' ? '/api/remove' : '/api/build', {
                            method: 'POST', headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({type: selectedTool, index: i})
                        });
                        update();
                    };
                    map.appendChild(tile);
                }
            }
            data.grid.forEach((cell, index) => {
                const t = document.getElementById('tile-' + index);
                t.innerHTML = cell !== 'empty' ? config[cell].icon : '';
                t.style.backgroundColor = cell !== 'empty' ? config[cell].color + '44' : '#1e293b';
                if(cell === 'road') t.style.backgroundColor = '#334155';
            });
        }
        function selectTool(t) { selectedTool = t; update(); }
        update();
        setInterval(update, 5000);
    </script>
</body>
</html>
html'''