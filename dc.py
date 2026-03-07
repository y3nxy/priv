import random
import string
import os
import asyncio
import aiohttp
from colorama import Fore, init
import datetime
import sys

# --- CONFIGURATION & INITIALIZATION ---
init(autoreset=True)
# Hardcoded as requested
WEBHOOK_URL = "https://discord.com/api/webhooks/1465728618524180736/tt_TWgwjFk1DNGzAhHABtnPqA90iXUWuwesqWgEW8gqXc8cUX_4q6UnxKltFTD1qOeN8"
CHECKED_FILE = "checked.txt"
AVAILABLE_FILE = "available_usernames.txt"
POMELO_URL = "https://discord.com/api/v9/users/@me/pomelo-attempt"
VALIDATE_URL = "https://discord.com/api/v9/users/@me"

# Colors
Lb, Ly, Lg, Lr, Lc = Fore.LIGHTBLACK_EX, Fore.LIGHTYELLOW_EX, Fore.LIGHTGREEN_EX, Fore.RED, Fore.LIGHTCYAN_EX

class Hunter:
    def __init__(self):
        self.tokens = []
        self.valid_tokens = []
        self.delay = 1.0
        self.checked_cache = set()
        self.token_idx = 0
        self.load_cache()
        # Open log with line buffering (buffering=1) to ensure progress is saved even if the script crashes
        self.checked_log = open(CHECKED_FILE, "a", encoding="utf-8", buffering=1)

    def load_cache(self):
        if not os.path.exists(CHECKED_FILE):
            open(CHECKED_FILE, "w").close()
        with open(CHECKED_FILE, "r", encoding="utf-8") as f:
            self.checked_cache = set(line.strip() for line in f if line.strip())
        print(f"{Lc}[*] Loaded {len(self.checked_cache)} previously checked names.")

    async def validate_all_tokens(self, session):
        print(f"{Ly}[*] Validating tokens... Please wait.")
        tasks = [self.check_single_token(session, t) for t in self.tokens]
        results = await asyncio.gather(*tasks)
        self.valid_tokens = [t for t in results if t is not None]
        
        if not self.valid_tokens:
            print(f"{Lr}[!] 0 Valid tokens found. Exiting.")
            sys.exit()
        print(f"{Lg}[+] Success: {len(self.valid_tokens)}/{len(self.tokens)} tokens are valid.")

    async def check_single_token(self, session, token):
        headers = {"Authorization": token}
        try:
            async with session.get(VALIDATE_URL, headers=headers, timeout=5) as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    print(f"{Lg}[V] Valid: {user_data.get('username', 'Unknown')}")
                    return token
                else:
                    return None
        except:
            return None

    def save_checked(self, username):
        if username not in self.checked_cache:
            self.checked_log.write(f"{username}\n")
            self.checked_cache.add(username)

    def log_available(self, username):
        with open(AVAILABLE_FILE, "a", encoding="utf-8") as f:
            f.write(f"{username}\n")

    def get_next_token(self):
        if not self.valid_tokens:
            return None
        token = self.valid_tokens[self.token_idx % len(self.valid_tokens)]
        self.token_idx += 1
        return token

    async def test_webhook(self, session):
        print(f"{Ly}[*] Testing Webhook...")
        payload = {"content": "✅ **Hunter V2.4 Started!** Monitor active."}
        try:
            async with session.post(WEBHOOK_URL, json=payload, timeout=5) as resp:
                if resp.status in [200, 204]:
                    print(f"{Lg}[+] Webhook is working.")
                else:
                    print(f"{Lr}[!] Webhook failed with status {resp.status}.")
        except Exception as e:
            print(f"{Lr}[!] Webhook Error: {e}")

    async def send_hit_webhook(self, session, username):
        payload = {
            "embeds": [{
                "title": "Username Available!",
                "description": f"The username `{username}` is available.",
                "color": 5763719,
                "footer": {"text": "Hunter V2.4 | Hardcore Mode"},
                "timestamp": str(datetime.datetime.utcnow())
            }]
        }
        try:
            await session.post(WEBHOOK_URL, json=payload, timeout=5)
        except:
            pass

    async def check_username(self, session, username):
        if username in self.checked_cache:
            print(f"{Lb}[~] Skipping {username} (Already Checked)")
            return True

        while True:
            token = self.get_next_token()
            if not token: 
                print(f"{Lr}[!] No valid tokens remaining.")
                return False

            headers = {
                "Authorization": token,
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            try:
                async with session.post(POMELO_URL, json={"username": username}, headers=headers, timeout=10) as resp:
                    if resp.status >= 500:
                        await asyncio.sleep(2)
                        continue

                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("taken") is False:
                            print(f"{Lg}[+] AVAILABLE: {username}")
                            self.log_available(username)
                            # Non-blocking hit notification
                            asyncio.create_task(self.send_hit_webhook(session, username))
                        else:
                            print(f"{Lr}[-] TAKEN: {username}")
                        
                        self.save_checked(username)
                        await asyncio.sleep(self.delay)
                        return True
                    
                    elif resp.status == 429:
                        data = await resp.json()
                        retry_after = data.get("retry_after", 5)
                        print(f"{Ly}[!] Rate Limited! Waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue 
                    
                    elif resp.status == 401:
                        print(f"{Lr}[?] Token died: {token[:10]}...")
                        if token in self.valid_tokens: 
                            self.valid_tokens.remove(token)
                            if len(self.valid_tokens) > 0:
                                self.token_idx %= len(self.valid_tokens)
                        continue
                    
                    else:
                        self.save_checked(username)
                        await asyncio.sleep(self.delay)
                        return True
                        
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(self.delay)
                return True

    async def run_list(self, session, filename):
        if not os.path.exists(filename):
            print(f"{Lr}Error: {filename} not found.")
            return
        with open(filename, "r") as f:
            names = [line.strip() for line in f if line.strip()]
        for name in names:
            if not await self.check_username(session, name): break

    async def run_gen(self, session, length, chars):
        print(f"{Ly}[*] Hunting... Press Ctrl+C to exit.")
        while True:
            name = ''.join(random.choice(chars) for _ in range(length))
            if not await self.check_username(session, name): break

async def main():
    print(f"{Lg}--- Discord Hunter V2.4 ---")
    hunter = Hunter()
    
    auth_mode = input(f"{Lc}Auth Mode:\n1. Single Token\n2. Multi Token (tokens.txt)\nSelection: ")
    if auth_mode == "1":
        t = input(f"{Lc}Paste Token: ").strip()
        if t: hunter.tokens = [t]
    else:
        file = input(f"{Lc}Filename: ")
        if os.path.exists(file):
            with open(file, "r") as f:
                hunter.tokens = [l.strip() for l in f if l.strip()]
    
    if not hunter.tokens:
        print(f"{Lr}No tokens loaded.")
        return

    try:
        hunter.delay = float(input(f"{Lc}Delay (e.g. 1.0): "))
    except ValueError:
        hunter.delay = 1.0

    async with aiohttp.ClientSession() as session:
        await hunter.validate_all_tokens(session)
        await hunter.test_webhook(session)

        print(f"\n{Ly}1. List\n2. 4-Char Mixed\n3. 4-Letter Only\n4. 3-Char Turbo")
        m = input("Selection: ")
        
        if m == "1": await hunter.run_list(session, "usernames.txt")
        elif m == "2": await hunter.run_gen(session, 4, string.ascii_lowercase + string.digits + "_.")
        elif m == "3": await hunter.run_gen(session, 4, string.ascii_lowercase)
        elif m == "4": await hunter.run_gen(session, 3, string.ascii_lowercase + string.digits)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Lr}[!] Closed. Progress saved in {CHECKED_FILE}")
        sys.exit()