import json
import requests
import random
import string

def handler(event, context):
    # Only allow POST requests from your website
    if event['httpMethod'] != 'POST':
        return {'statusCode': 405, 'body': 'Method Not Allowed'}

    try:
        # Get data from the website
        data = json.loads(event['body'])
        token = data.get('token')
        mode = data.get('mode')
        webhook = data.get('webhook')

        # Username Generation Logic
        if mode == "4": # 3-Char Turbo
            username = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
        elif mode == "3": # 4-Letter Only
            username = ''.join(random.choice(string.ascii_lowercase) for _ in range(4))
        else: # 4-Char Mixed (Default)
            username = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))

        headers = {
            "Authorization": token, 
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        # Check Discord API
        r = requests.post(
            "https://discord.com/api/v9/users/@me/pomelo-attempt", 
            json={"username": username}, 
            headers=headers, 
            timeout=5
        )
        
        res_payload = {
            "username": username,
            "status": r.status_code
        }
        
        if r.status_code == 200:
            is_taken = r.json().get("taken")
            res_payload["taken"] = is_taken
            
            # Send to Webhook if Available
            if is_taken is False and webhook:
                requests.post(webhook, json={
                    "content": f"**AVAILABLE:** `{username}`\nChecked by **Discord Hunter V2.4** | MADE BY Y3NXY"
                })
        elif r.status_code == 429:
            res_payload["retry_after"] = r.json().get("retry_after", 5)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(res_payload)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }
