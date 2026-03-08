from flask import Flask, render_template, request, jsonify
import threading
import string
import random
import requests
import time
import os

app = Flask(__name__)

# Global state
stats = {"checked": 0, "available": 0, "taken": 0, "cpm": 0}
logs = []
running = False

def get_random_user(mode):
    if mode == "2": # 4-Char Mixed
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))
    elif mode == "3": # 4-Letter Only
        return ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
    elif mode == "4": # 3-Char Turbo
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    return None

def checker_logic(config):
    global running, logs, stats
    
    tokens = [config['token']] # Default to single token
    # If they want multi-token, we look for tokens.txt
    if os.path.exists("tokens.txt"):
        with open("tokens.txt", "r") as f:
            file_tokens = [l.strip() for l in f if l.strip()]
            if file_tokens: tokens = file_tokens

    logs.append(f"[+] Loaded {len(tokens)} token(s)")
    logs.append("[*] Starting hunt... Press Stop to exit.")
    
    start_time = time.time()
    token_idx = 0
    
    # Mode 1: List mode needs a file
    user_list = []
    if config['mode'] == "1":
        if os.path.exists("usernames.txt"):
            with open("usernames.txt", "r") as f:
                user_list = [l.strip() for l in f if l.strip()]
        else:
            logs.append("[!] usernames.txt not found!")
            running = False
            return

    while running:
        # Determine username to check
        if config['mode'] == "1":
            if not user_list: break
            username = user_list.pop(0)
        else:
            username = get_random_user(config['mode'])

        current_token = tokens[token_idx % len(tokens)]
        headers = {"Authorization": current_token, "Content-Type": "application/json"}
        
        try:
            r = requests.post("https://discord.com/api/v9/users/@me/pomelo-attempt", 
                             json={"username": username}, headers=headers, timeout=5)
            
            if r.status_code == 200:
                stats["checked"] += 1
                is_taken = r.json().get("taken")
                
                if is_taken is False:
                    stats["available"] += 1
                    logs.append(f"[{stats['checked']}] AVAILABLE: {username}")
                    if config['webhook']:
                        requests.post(config['webhook'], json={"content": f"AVAILABLE: {username} | MADE BY Y3NXY"})
                else:
                    stats["taken"] += 1
                    logs.append(f"[{stats['checked']}] TAKEN: {username}")
                
                token_idx += 1 # Rotate token
            
            elif r.status_code == 429:
                logs.append("[!] Rate limited. Rotating token...")
                token_idx += 1
                time.sleep(1)
                continue
            
            elif r.status_code == 401:
                logs.append(f"[!] Token invalid: {current_token[:10]}...")
                tokens.pop(token_idx % len(tokens))
                if not tokens: 
                    logs.append("[!] No valid tokens left!")
                    break

            # Update Stats
            elapsed = (time.time() - start_time) / 60
            stats["cpm"] = int(stats["checked"] / elapsed) if elapsed > 0 else 0
            
            time.sleep(float(config.get('delay', 1.0)))

        except Exception as e:
            time.sleep(1)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/test_webhook', methods=['POST'])
def test_webhook():
    url = request.json.get('url')
    if url: requests.post(url, json={"content": "[*] Webhook Test Successful - MADE BY Y3NXY"})
    return jsonify({"status": "sent"})

@app.route('/start', methods=['POST'])
def start():
    global running, stats, logs
    if not running:
        stats = {"checked": 0, "available": 0, "taken": 0, "cpm": 0}
        logs = []
        running = True
        threading.Thread(target=checker_logic, args=(request.json,), daemon=True).start()
    return jsonify({"status": "started"})

@app.route('/stats')
def get_stats():
    global logs
    current_logs = logs[:]
    logs = []
    return jsonify({"stats": stats, "logs": current_logs})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
