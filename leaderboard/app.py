from flask import Flask, jsonify, request
from utils import update_leaderboard, get_top_leaderboard, enable_cors

app = Flask(__name__)
enable_cors(app)

@app.route('/leaderboard/update', methods=['POST'])
def update():
    data = request.json
    user_id = data.get("user_id")
    total_points = data.get("total_points")
    update_leaderboard(user_id, total_points)
    return jsonify({"status": "Leaderboard updated"}), 200

@app.route('/leaderboard/top', methods=['GET'])
def top():
    return jsonify(get_top_leaderboard())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5404)




# from flask import Flask, jsonify
# from dotenv import load_dotenv
# from utils import get_top_users, get_user_rank, supabase
# import os

# load_dotenv()
# app = Flask(__name__)

# @app.route('/leaderboard/top', methods=['GET'])
# def top_leaderboard():
#     top_users = get_top_users()
#     return jsonify(top_users), 200

# @app.route('/leaderboard/user/<user_id>', methods=['GET'])
# def user_rank(user_id):
#     rank_info = get_user_rank(user_id)
#     return jsonify(rank_info), 200



# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5404)