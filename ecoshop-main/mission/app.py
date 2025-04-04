from flask import Flask, request, jsonify
from dotenv import load_dotenv
from utils import update_mission_progress, get_user_missions, list_all_missions, supabase
import os

load_dotenv()
app = Flask(__name__)

@app.route('/mission/update', methods=['POST'])
def update_mission():
    data = request.get_json()
    user_id = data.get('user_id')
    event_type = data.get('event_type')
    if not user_id or not event_type:
        return jsonify({'error': 'Missing data'}), 400
    result = update_mission_progress(user_id, event_type)
    return jsonify(result), 200

@app.route('/mission/status/<user_id>', methods=['GET'])
def mission_status(user_id):
    status = get_user_missions(user_id)
    return jsonify(status), 200

@app.route('/mission/all', methods=['GET'])
def mission_list():
    missions = list_all_missions()
    return jsonify(missions), 200

@app.route("/mission/check/<user_id>/<event_type>")
def check_user_mission(user_id, event_type):
    try:
        # Get missions matching event_type
        missions = supabase.table("mission").select("*").eq("event_type", event_type).execute().data
        if not missions:
            return jsonify({"should_update": False}), 200

        mission_ids = [m["id"] for m in missions]

        # Check if user joined any
        user_missions = supabase.table("user_missions").select("*")\
            .eq("user_id", user_id).in_("mission_id", mission_ids).execute().data

        if user_missions:
            return jsonify({"should_update": True}), 200
        else:
            return jsonify({"should_update": False}), 200
    except Exception as e:
        print(f"[!] Mission check error: {e}")
        return jsonify({"should_update": False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5403)