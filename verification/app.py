from flask import Flask, render_template, request, redirect
from dotenv import load_dotenv
from utils import list_pending_trades, update_trade_status, enable_cors
import os
from utils import supabase

load_dotenv()
app = Flask(__name__)
enable_cors(app)

@app.route('/')
def dashboard():
    trades = supabase.from_("trade_ins").select("*").order("created_at", desc=True).execute().data
    return render_template("index.html", trades=trades)

@app.route('/verify/<int:trade_id>', methods=['POST'])
def verify_trade(trade_id):
    action = request.form.get("action")
    if action not in ["accepted", "rejected"]:
        return "Invalid action", 400

    updated = update_trade_status(trade_id, action)
    return redirect('/')
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5401)
