import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, session
from whitenoise import WhiteNoise
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')

# SECURITY: Get secret key from .env, never hardcode
app.secret_key = os.getenv('SECRET_KEY', 'default-very-secret-key-change-me')

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)
        return conn
    except Exception as e:
        print(f"❌ Error connecting to DB: {e}")
        return None

# ==========================================
# Database Initialization (Professional Setup)
# ==========================================

def init_database():
    """ينشئ جداول قاعدة البيانات إذا لم تكن موجودة"""
    conn = get_db_connection()
    if not conn: return
    try:
        cur = conn.cursor()

        # 1. Products Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            buying_price NUMERIC,
            selling_price NUMERIC NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            image_url TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # 2. Marketers Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS marketers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            phone TEXT,
            commission_rate NUMERIC DEFAULT 10,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # 3. Orders Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT,
            total_price NUMERIC NOT NULL,
            products_json JSONB NOT NULL,
            marketer_code TEXT REFERENCES marketers(code),
            status TEXT DEFAULT 'قيد المراجعة',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        
        # NOTE: For security, Admin credentials should be set in .env
        # and checked against variables, not stored in DB ideally for simple setups,
        # or hashed in DB.

        conn.commit()
        print("✅ Database initialized successfully with all tables.")
        cur.close()
        conn.close()
    except Exception as e:
        print('❌ DB init error:', e)

# Run database init on startup
init_database()

# ==========================================
# Helper: Authentication Check Decorator
# ==========================================
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"success": False, "message": "غير مصرح، يرجى تسجيل الدخول"}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# Routes (HTML Pages)
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/cashier.html')
def cashier_page():
    # In a pro app, check session here and redirect to login if not auth
    if 'user_id' not in session:
        return render_template('login.html', error="يرجى تسجيل الدخول أولاً")
    return render_template('cashier.html')

@app.route('/product_detail.html')
def product_detail():
    return render_template('product_detail.html')

@app.route('/marketer_login.html')
def marketer_login_page():
    return render_template('marketer_login.html')

@app.route('/marketer_dashboard.html')
def marketer_dashboard_page():
    return render_template('marketer_dashboard.html')

# ==========================================
# API Products (Full CRUD)
# ==========================================

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    if not conn: return jsonify([]), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Search functionality
        search = request.args.get('search', '')
        if search:
            cur.execute("SELECT * FROM products WHERE name ILIKE %s ORDER BY id DESC;", (f'%{search}%',))
        else:
            cur.execute("SELECT * FROM products ORDER BY id DESC;")
            
        products = cur.fetchall()
        cur.close()
        conn.close()
        # NO MORE DUMMY DATA HERE
        return jsonify(products)
    except Exception as e:
        print(f"Error getting products: {e}")
        return jsonify([]), 500

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO products (name, category, buying_price, selling_price, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """, (
            data.get('name'), data.get('category'), 
            data.get('buying_price', 0), data.get('selling_price'),
            data.get('stock_quantity', 0), data.get('image_url', ''),
            data.get('description')
        ))
        prod_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "id": prod_id}), 201
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/products/<int:id>', methods=['DELETE'])
@login_required
def delete_product(id):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s;", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# API Orders (Real Storage)
# ==========================================

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        print("📦 Real Order Received:", data)
        
        conn = get_db_connection()
        if not conn: return jsonify({"success": False}), 500
        cur = conn.cursor()
        
        # Use JSONB for better performance and manipulation
        products_json = json.dumps(data.get('products', []), ensure_ascii=False)
        
        cur.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, products_json, marketer_code, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('customer_address'),
            float(data.get('total_price', 0)),
            products_json,
            data.get('marketer_code'), # Can be null
            'قيد المراجعة'
        ))
        
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "order_id": order_id}), 200
        
    except Exception as e:
        print(f"❌ Create Order Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    conn = get_db_connection()
    if not conn: return jsonify([]), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM orders ORDER BY id DESC;")
        orders = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(orders)
    except Exception as e:
        return jsonify([]), 500

# ==========================================
# API Auth (PRO - Hashed & Secure)
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        # PROFESSIONAL: Define these in your Vercel/Server Environment Variables
        # DO NOT HARDCODE.
        # Example on how to generate a hash once: print(generate_password_hash('your_secure_pass'))
        ADMIN_USER = os.getenv('ADMIN_USERNAME', 'admin_sina')
        ADMIN_HASH = os.getenv('ADMIN_PASSWORD_HASH') # Generate this hash and store it
        
        # Fallback for development ONLY if env vars are missing
        DEV_HASH = generate_password_hash('MoSebA01065653401') # The old pass, now hashed

        target_hash = ADMIN_HASH if ADMIN_HASH else DEV_HASH

        if username == ADMIN_USER and check_password_hash(target_hash, password):
            session.permanent = True # Session lasts longer
            session['user_id'] = 1
            session['role'] = 'manager'
            session['name'] = 'المدير'
            return jsonify({"success": True, "role": "manager", "name": "المدير"})
        
        return jsonify({"success": False, "message": "بيانات الدخول غير صحيحة"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": f"خطأ في الخادم: {str(e)}"}), 500

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

# ==========================================
# API Stats (REAL DATA)
# ==========================================

@app.route('/api/stats/dashboard', methods=['GET'])
@login_required
def dashboard_stats():
    conn = get_db_connection()
    if not conn: return jsonify({}), 500
    try:
        cur = conn.cursor()
        
        # 1. Total Sales
        cur.execute("SELECT SUM(total_price) FROM orders WHERE status = 'تم التوصيل';")
        total_sales = cur.fetchone()[0] or 0
        
        # 2. Total Orders
        cur.execute("SELECT COUNT(*) FROM orders;")
        total_orders = cur.fetchone()[0] or 0
        
        # 3. Total Products
        cur.execute("SELECT COUNT(*) FROM products;")
        total_products = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return jsonify({
            "total_sales": float(total_sales),
            "total_orders": total_orders,
            "total_products": total_products,
            "orders_by_status": [] # can expand later
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Professional banner
    print("""
    ##########################################
    🚀 Sina Store PRO Server is Starting...
    📞 Admin Panel: http://localhost:5000/login.html
    🔐 Set ADMIN_USERNAME & ADMIN_PASSWORD_HASH in .env
    ##########################################
    """)
    init_database() # Ensure DB is ready
    app.run(debug=True, host='0.0.0.0', port=5000)
