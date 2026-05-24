import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, session
from whitenoise import WhiteNoise
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)

# ==========================================
# تم تعطيل حذف الطلبات التلقائي لحماية البيانات
# ==========================================


# ==========================================
# إنشاء باقي الجداول
# ==========================================

def init_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # جدول المنتجات
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                selling_price REAL DEFAULT 0,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # جدول المستخدمين
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'admin',
                name TEXT
            );
        """)
        
        conn.commit()
        
        # إضافة مستخدم admin
        hashed = generate_password_hash(os.getenv('ADMIN_PASSWORD', 'admin123'))
        cur.execute("""
            INSERT INTO users (username, password, role, name)
            SELECT 'admin', %s, 'manager', 'المدير'
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');
        """, (hashed,))
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database initialized!")
    except Exception as e:
        print(f"Init error: {e}")

init_database()

# ==========================================
# Routes
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/cashier.html')
def cashier_page():
    return render_template('cashier.html')

@app.route('/product_detail.html')
def product_detail():
    return render_template('product_detail.html')

# ==========================================
# API Products
# ==========================================

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id DESC;")
        products = cur.fetchall()
        cur.close()
        conn.close()
        
        # إذا كان جدول المنتجات فاضي، أضف منتجات تجريبية
        if len(products) == 0:
            products = [
                {"id": 1, "name": "كفر شفاف ايفون 13", "category": "كفرات", "selling_price": 50, "image_url": "", "description": "كفر شفاف حماية كاملة"},
                {"id": 2, "name": "شاحن سريع 20W", "category": "شواحن", "selling_price": 150, "image_url": "", "description": "شاحن سريع بقوة 20 واط"},
                {"id": 3, "name": "سماعة بلوتوث", "category": "سماعات", "selling_price": 200, "image_url": "", "description": "سماعة لاسلكية بتقنية بلوتوث"},
            ]
        
        return jsonify(products)
    except Exception as e:
        return jsonify([{"id": 1, "name": "منتج تجريبي", "selling_price": 100}]), 500

# ==========================================
# API Orders - أبسط نسخة ممكنة
# ==========================================

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        print("📦 الطلب المستلم:", data)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # تحويل المنتجات إلى نص JSON
        products_json = json.dumps(data.get('products', []), ensure_ascii=False)
        
        # إدراج الطلب
        cur.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, products_json, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('customer_address'),
            float(data.get('total_price', 0)),
            products_json,
            'قيد المراجعة'
        ))
        
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ تم إنشاء الطلب رقم: {order_id}")
        return jsonify({"success": True, "order_id": order_id}), 200
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM orders ORDER BY id DESC;")
        orders = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(orders)
    except Exception as e:
        return jsonify([]), 500

# ==========================================
# API Auth مبسط
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        if data.get('username') == 'admin' and data.get('password') == 'MoSebA01065653401':
            session['user_id'] = 1
            session['role'] = 'manager'
            session['name'] = 'المدير'
            return jsonify({"success": True, "role": "manager", "name": "المدير"})
        return jsonify({"success": False, "message": "بيانات غير صحيحة"}), 401
    except:
        return jsonify({"success": False, "message": "خطأ"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    return jsonify({
        "authenticated": 'user_id' in session,
        "role": session.get('role'),
        "name": session.get('name')
    })

@app.route('/api/stats/dashboard', methods=['GET'])
def dashboard_stats():
    return jsonify({
        "total_sales": 0,
        "total_orders": 0,
        "total_products": 3,
        "total_marketers": 0,
        "orders_by_status": []
    })

# ==========================================
# Marketer APIs مبسطة
# ==========================================

@app.route('/api/marketer/check', methods=['GET'])
def check_marketer():
    return jsonify({"authenticated": False})

@app.route('/marketer_login.html')
def marketer_login():
    return render_template('marketer_login.html')

@app.route('/marketer_dashboard.html')
def marketer_dashboard():
    return render_template('marketer_dashboard.html')

if __name__ == '__main__':
    print("🚀 سيرفر سينا ستور شغال...")
    print("📞 عنوان المتجر: http://localhost:5000")
    print("🔐 دخول المدير: admin / MoSebA01065653401")
    app.run(debug=True, host='0.0.0.0', port=5000)
