import urllib.request
import json
import time

url = 'http://127.0.0.1:5000/api/chat'
headers = {'Content-Type': 'application/json'}

def send(msg):
    req = urllib.request.Request(url, data=json.dumps({"question": msg}).encode(), headers=headers)
    try:
        res = urllib.request.urlopen(req)
        print("SUCCESS:", res.read().decode()[:100] + "...")
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR {e.code}: {e.read().decode()}")
    except Exception as e:
        print("ERROR:", str(e))

print("Sending first msg...")
send("Hello")

time.sleep(1)

print("Sending second msg...")
send("How are you?")
