import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for

# إعداد ذكي للمسارات: جعل Flask يقرأ من الجذر ومن فولدر templates معاً لمنع الانهيار
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

# رابط الاتصال المباشر بقاعدة بيانات سوبابيس
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

# --- 🌐 مسارات الصفحات ---

@app.route('/')
def index():
    # تعديل خاص لبيئة Vercel: إذا كان index.html برة، يقرأه مباشرة، وإلا يقرأه من templates
    main_index_path = os.path.join(BASE_DIR, 'index.html')
    if os.path.exists(main_index_path):
        with open(main_index_path, 'r', encoding='utf-8') as f:
            return f.read()
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
        
        selling_price = float(data.get('selling_price', 0) or 0)
        purchasing_price = float(data.get('purchasing_price', 0) or 0)
        commission = float(data.get('commission', 0) or 0)
        stock_quantity = int(data.get('stock_quantity', 0) or 0)

        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'), 
            data.get('category', 'عام'), 
            selling_price,
            purchasing_price,
            commission,
            stock_quantity,
            data.get('image_url'), 
            data.get('description', '')
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

# --- 📦 واجهات الطلبات ---

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        total_val = data.get('total_price') or data.get('total_val') or 0
        products_json_str = json.dumps(data.get('products', []), ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data.get('customer_name'), 
            data.get('customer_phone'), 
            data.get('customer_address'), 
            float(total_val), 
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

if __name__ == '__main__':
    app.run(debug=True)
