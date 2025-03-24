from flask import Flask, request, jsonify
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Table name for missions
MISSIONS_TABLE = "missions"

# Helper function to validate mission data
def validate_mission_data(data):
    required_fields = ["title", "description", "points"]
    for field in required_fields:
        if field not in data:
            return False
    return True

# GET /missions - Get all missions
@app.route("/missions", methods=["GET"])
def get_missions():
    try:
        response = supabase.table(MISSIONS_TABLE).select("*").execute()
        missions = response.data
        return jsonify(missions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GET /missions/<mission_id> - Get a specific mission by ID
@app.route("/missions/<int:mission_id>", methods=["GET"])
def get_mission(mission_id):
    try:
        response = supabase.table(MISSIONS_TABLE).select("*").eq("id", mission_id).execute()
        mission = response.data
        if mission:
            return jsonify(mission[0]), 200
        else:
            return jsonify({"error": "Mission not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# POST /missions - Create a new mission
@app.route("/missions", methods=["POST"])
def create_mission():
    try:
        data = request.get_json()
        if not validate_mission_data(data):
            return jsonify({"error": "Invalid mission data"}), 400

        # Insert mission into Supabase
        response = supabase.table(MISSIONS_TABLE).insert(data).execute()
        new_mission = response.data[0]
        return jsonify(new_mission), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# PUT /missions/<mission_id> - Update a mission by ID
@app.route("/missions/<int:mission_id>", methods=["PUT"])
def update_mission(mission_id):
    try:
        data = request.get_json()
        if not validate_mission_data(data):
            return jsonify({"error": "Invalid mission data"}), 400

        # Update mission in Supabase
        response = supabase.table(MISSIONS_TABLE).update(data).eq("id", mission_id).execute()
        updated_mission = response.data
        if updated_mission:
            return jsonify(updated_mission[0]), 200
        else:
            return jsonify({"error": "Mission not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# DELETE /missions/<mission_id> - Delete a mission by ID
@app.route("/missions/<int:mission_id>", methods=["DELETE"])
def delete_mission(mission_id):
    try:
        # Delete mission from Supabase
        response = supabase.table(MISSIONS_TABLE).delete().eq("id", mission_id).execute()
        if response.data:
            return jsonify({"message": "Mission deleted successfully"}), 200
        else:
            return jsonify({"error": "Mission not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


    
# Function to run the Flask app
def run_flask_app():
    app.run(host='0.0.0.0', port=5401)

if __name__ == '__main__':
    # Start the Flask app in a separate thread
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

