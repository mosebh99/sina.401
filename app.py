import os
import sqlite3
import json
from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

if os.environ.get('VERCEL') or os.environ.get('RENDER') or 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    DB_FILE = "/tmp/database.db"
else:
    DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            selling_price REAL NOT NULL,
            stock_quantity INTEGER,
            image_url TEXT NOT NULL,
            description TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            total_price REAL NOT NULL,
            marketer_id TEXT,
            products_json TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/cashier.html')
def cashier(): return render_template('cashier.html')

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
        # هنا بنضمن إن السيرفر يقبل المسميات القديمة والجديدة مع بعض عشان ميهنجش
        name = data.get('name') or data.get('p-name')
        price = data.get('selling_price') or data.get('p-price') or 0
        stock = data.get('stock_quantity') or data.get('p-stock') or 0
        img = data.get('image_url') or data.get('image') or 'logo.png'
        desc = data.get('description') or data.get('p-desc') or ''
        cat = data.get('category') or 'عام'

        cursor.execute('''
            INSERT INTO products (name, category, selling_price, stock_quantity, image_url, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, cat, float(price), int(stock), img, desc))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['PUT'])
def update_product(p_id):
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=?, selling_price=?, stock_quantity=?, image_url=?, description=?
            WHERE id=?
        ''', (data['name'], float(data['selling_price']), int(data['stock_quantity']), data['image_url'], data['description'], p_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['DELETE'])
def delete_product(p_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

handler = app
if __name__ == '__main__':
    app.run(debug=True)
