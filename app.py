import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for

# ضبط مسار المجلد الرئيسي لـ Vercel لقرأة ملفات الـ HTML من الجذر مباشرة
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)

# رابط الاتصال المباشر والمستقر بقاعدة البيانات
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # إنشاء جدول المنتجات الأساسي
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
        # إنشاء جدول الطلبات الأساسي
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_address TEXT NOT NULL,
                total_price REAL NOT NULL,
                marketer_id TEXT,
                products_json TEXT NOT NULL,
                status TEXT DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("🚀 Database initialized successfully!")
    except Exception as e:
        print("❌ Database Init Error:", e)

# تشغيل الفحص الأولي
init_db()

# --- 🌐 مسارات العرض والتوجيه المباشر ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/index.html')
def index_html():
    return redirect(url_for('index'))

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/cashier.html')
def cashier():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

# --- 🛒 واجهات الـ API الخاصة بالمنتجات ---

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
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # التأكد من معالجة القيم بشكل صحيح وآمن لمنع الأخطاء الحسابية
        selling_price = float(data.get('selling_price', 0) or 0)
        purchasing_price = float(data.get('purchasing_price', 0) or 0)
        commission = float(data.get('commission', 0) or 0)
        stock_quantity = int(data.get('stock_quantity', 0) or 0)

        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'), data.get('category', 'عام'), 
            selling_price, purchasing_price, commission, stock_quantity,
            data.get('image_url'), data.get('description', '')
        ))
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

# --- 📦 واجهات الـ API الخاصة بالطلبات ---

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        products_json_str = json.dumps(data.get('products', []), ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('customer_name'), 
            data.get('customer_phone'), 
            data.get('customer_address'), 
            float(data.get('total_price', 0)), 
            data.get('marketer_id'), 
            products_json_str
        ))
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
    data = request.get_json() or {}
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
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
