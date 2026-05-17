import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

# 🔗 حط هنا الرابط اللي جبناه من Supabase (تأكد إن الباسورد مكتوبة جواه صح مكان [YOUR-PASSWORD])
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    # الاتصال بقاعدة البيانات السحابية Supabase بدلاً من sqlite3 المؤقتة
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # إنشاء جدول المنتجات الدائم في Supabase
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'عام',
            selling_price REAL NOT NULL,
            purchasing_price REAL DEFAULT 0,
            commission REAL DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            image_url TEXT,
            description TEXT
        )
    ''')
    # إنشاء جدول الطلبات الدائم في Supabase
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
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
    cursor.close()
    conn.close()

# تهيئة قاعدة البيانات عند تشغيل السيرفر
try:
    init_db()
except Exception as e:
    print("Database connection/init error:", e)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/cashier.html')
def cashier(): return render_template('cashier.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify([]), 200

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        name = data.get('name')
        price = data.get('selling_price') or 0
        p_price = data.get('purchasing_price') or 0
        comm = data.get('commission') or 0
        stock = data.get('stock_quantity') or 0
        img = data.get('image_url') or ''
        desc = data.get('description') or ''
        cat = data.get('category') or 'عام'

        # استخدام %s بدلاً من ? لأنها قاعدة بيانات PostgreSQL
        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (name, cat, float(price), float(p_price), float(comm), int(stock), img, desc))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['DELETE'])
def delete_product(p_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=%s", (p_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        products_json_str = json.dumps(data['products'], ensure_ascii=False)
        total_val = data.get('total') or data.get('total_price') or 0
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (data['customer_name'], data['customer_phone'], data['customer_address'], float(total_val), data.get('marketer_id'), products_json_str))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM orders ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify([]), 200

@app.route('/api/orders/<int:o_id>', methods=['PUT'])
def update_order_status(o_id):
    data = request.get_json()
    status = data.get('status')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, o_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

handler = app
if __name__ == '__main__':
    app.run(debug=True)
