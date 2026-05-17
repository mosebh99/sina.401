import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for

# ضبط المسار لقرأة ملفات الـ HTML من الفولدر الرئيسي مباشرة كما هي بمشروعك
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)

# رابط الاتصال المباشر بقاعدة بيانات سوبابيس
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # إنشاء الجدول بالخصائص الأساسية المتوافقة تماماً مع صفحة cashier.html الحالية لديك
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
        print("🚀 Database Ready!")
    except Exception as e:
        print("❌ Database Init Error:", e)

init_db()

# --- 🌐 مسارات الصفحات ---

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

# --- 🛒 واجهات الـ API (متوافقة 100% مع طلبات صفحة cashier و index) ---

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
        
        # استقبال البيانات بالشكل الأساسي الذي ترسله واجهتك الحالية لمنع أي خطأ
        cursor.execute('''
            INSERT INTO products (name, category, selling_price, image_url, description)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            data.get('name'), 
            data.get('category', 'عام'), 
            float(data.get('selling_price', 0) or 0), 
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
        
        # معالجة إجمالي الطلب سواء كان الاسم total_price أو total_val لضمان عدم حدوث خطأ
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
