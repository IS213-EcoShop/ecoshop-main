from flask import Flask
from dotenv import load_dotenv
from events import start_event_listener
import os



load_dotenv()
app = Flask(__name__)

@app.route('/')
def health():
    return {'status': 'reward orchestrator running'}, 200

if __name__ == '__main__':
    print("[*] Starting Reward Orchestrator...")
    start_event_listener()
    app.run(host='0.0.0.0', port=5405)