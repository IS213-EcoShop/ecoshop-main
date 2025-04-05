from flask import Flask, request, jsonify
from utils import list_voucher_templates, claim_voucher
from utils.cors_config import enable_cors

app = Flask(__name__)
enable_cors(app)

@app.route("/voucher/templates", methods=["GET"])
def get_templates():
    return jsonify(list_voucher_templates())

@app.route("/voucher/claim", methods=["POST"])
def claim():
    data = request.json
    user_id = data.get("user_id")
    voucher_id = data.get("voucher_id")
    return claim_voucher(user_id, voucher_id)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5406)
