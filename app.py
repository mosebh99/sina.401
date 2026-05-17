import os
import sqlite3
import json
from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

# مسار قاعدة البيانات الآمن للسيرفرات السحابية والمحلية
if os.environ.get('VERCEL') or os.environ.get('RENDER') or 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    DB_FILE = "/tmp/database.db"
else:
    DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # جدول المنتجات الشامل (يدعم سعر الشراء والعمولة للربحية)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'عام',
            selling_price REAL NOT NULL,
            purchasing_price REAL DEFAULT 0,
            commission REAL DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            image_url TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # جدول الطلبات الشامل (يدعم التتبع وكود المسوق)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            total_price REAL NOT NULL,
            marketer_id TEXT,
            products_json TEXT NOT NULL,
            status TEXT DEFAULT 'قيد المراجعة ⏳'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/cashier.html')
def cashier(): return render_template('cashier.html')

# --- تشغيل وبوابات المنتجات ---
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        name = data.get('name')
        price = data.get('selling_price') or 0
        p_price = data.get('purchasing_price') or 0
        comm = data.get('commission') or 0
        stock = data.get('stock_quantity') or 0
        img = data.get('image_url') or 'logo.png'
        desc = data.get('description') or ''
        cat = data.get('category') or 'عام'

        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, cat, float(price), float(p_price), float(comm), int(stock), img, desc))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['DELETE'])
def delete_product(p_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

# --- تشغيل وبوابات الطلبات والتتبع ---
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        products_json_str = json.dumps(data['products'], ensure_ascii=False)
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['customer_name'], data['customer_phone'], data['customer_address'], float(data['total']), data.get('marketer_id'), products_json_str))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e: return jsonify({"status": "error"}), 400

@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows]), 200

@app.route('/api/orders/<int:o_id>', methods=['PUT'])
def update_order_status(o_id):
    data = request.get_json()
    status = data.get('status')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=? WHERE id=?", (status, o_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"}), 200

handler = app
if __name__ == '__main__':
    app.run(debug=True)
