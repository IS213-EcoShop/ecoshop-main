from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
