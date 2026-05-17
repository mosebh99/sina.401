from flask import Flask, jsonify, request, render_template
import os

app = Flask(__name__, template_folder='.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cashier.html')
def cashier():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    print("New Order Received:", data)
    return jsonify({"status": "success", "message": "Order registered successfully"}), 200

# المتغير الرئيسي لتتعرف عليه منصة Vercel كـ Handler
application = app

if __name__ == '__main__':
    app.run(debug=True)
