from flask import Flask, request, jsonify
from dotenv import load_dotenv
from utils import upload_image_to_supabase, create_trade_in, get_trade_status
import os
from utils.cors_config import enable_cors

load_dotenv()

app = Flask(__name__)
enable_cors(app)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/trade-in/request', methods=['POST'])
def submit_trade_in():
    user_id = request.form.get('user_id')
    product_name = request.form.get('product_name')
    image = request.files.get('image')

    if not user_id or not product_name or not image:
        return jsonify({'error': 'Missing required fields'}), 400

    if not allowed_file(image.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    filename, image_url = upload_image_to_supabase(image)
    new_trade = create_trade_in(user_id, product_name, image_url)

    return jsonify({
        'message': 'Trade-In submitted',
        'trade_id': new_trade["id"],
        'image_url': new_trade["image_url"]
    }), 201

@app.route('/trade-in/status/<int:trade_id>', methods=['GET'])
def get_status(trade_id):
    trade = get_trade_status(trade_id)
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404
    return jsonify(trade), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5400)
