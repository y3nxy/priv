import random, string, os, asyncio, aiohttp, datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hunter_secret_key'
socket_io = SocketIO(app, cors_allowed_origins="*")

# --- CONFIG ---
WEBHOOK_URL = "https://discord.com/api/webhooks/1465728618524180736/tt_TWgwjFk1DNGzAhHABtnPqA90iXUWuwesqWgEW8gqXc8cUX_4q6UnxKltFTD1qOeN8"
POMELO_URL = "https://discord.com/api/v9/users/@me/pomelo-attempt"
CHECKED_FILE = "checked.txt"

class WebHunter:
    def __init__(self):
        self.tokens = []
        self.delay = 1.0
        self.running = False
        self.checked_cache = set()
        self.load_cache()

    def load_cache(self):
        if os.path.exists(CHECKED_FILE):
            with open(CHECKED_FILE, "r") as f:
                self.checked_cache = set(line.strip() for line in f if line.strip())

    def save_checked(self, username):
        if username not in self.checked_cache:
            with open(CHECKED_FILE, "a") as f:
                f.write(f"{username}\n")
            self.checked_cache.add(username)

    async def log(self, message, color="white"):
        socket_io.emit('log', {'msg': message, 'color': color})

    async def send_webhook(self, session, username):
        payload = {
            "embeds": [{
                "title": "Available!", 
                "description": f"Username `{username}` is available.", 
                "color": 5763719,
                "timestamp": str(datetime.datetime.utcnow())
            }]
        }
        try:
            await session.post(WEBHOOK_URL, json=payload)
        except:
            pass

    async def start(self, length, delay, tokens):
        self.tokens = tokens
        self.delay = delay
        self.running = True
        token_idx = 0
        
        async with aiohttp.ClientSession() as session:
            await self.log("🚀 Hunter Started...", "#00ff00")
            
            while self.running:
                username = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
                
                if username in self.checked_cache:
                    continue

                token = self.tokens[token_idx % len(self.tokens)]
                token_idx += 1
                
                headers = {"Authorization": token, "Content-Type": "application/json"}
                try:
                    async with session.post(POMELO_URL, json={"username": username}, headers=headers, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if not data.get("taken"):
                                await self.log(f"[+] AVAILABLE: {username}", "#00ff00")
                                await self.send_webhook(session, username)
                            else:
                                await self.log(f"[-] TAKEN: {username}", "#ff4444")
                            
                            self.save_checked(username)
                            
                        elif resp.status == 429:
                            await self.log("⚠️ Rate Limited! Waiting 5s...", "#ffff00")
                            await asyncio.sleep(5)
                        
                        elif resp.status == 401:
                            await self.log(f"❌ Token Dead: {token[:10]}...", "#ff4444")
                except Exception as e:
                    await self.log(f"Error: {str(e)}", "gray")
                
                await asyncio.sleep(self.delay)
            
            await self.log("🛑 Hunter Stopped.", "#9147ff")

hunter = WebHunter()

@app.route('/')
def index():
    return render_template('index.html')

@socket_io.on('start_hunt')
def handle_start(data):
    if hunter.running:
        socket_io.emit('log', {'msg': 'Hunter is already running!', 'color': '#ffff00'})
        return

    tokens = [t.strip() for t in data['tokens'].split('\n') if t.strip()]
    delay = float(data.get('delay', 1.0))
    length = int(data.get('length', 4))
    
    # Start in background task so Flask can keep running
    socket_io.start_background_task(run_async_hunter, length, delay, tokens)

def run_async_hunter(length, delay, tokens):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(hunter.start(length, delay, tokens))

@socket_io.on('stop_hunt')
def handle_stop():
    hunter.running = False

if __name__ == '__main__':
    socket_io.run(app, debug=True)