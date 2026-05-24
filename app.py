import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session
from whitenoise import WhiteNoise
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2026')

DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)

# ==========================================
# تحديث قاعدة البيانات تلقائياً
# ==========================================

def migrate_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # إضافة الأعمدة المفقودة إلى orders
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='marketer_code') THEN
                    ALTER TABLE orders ADD COLUMN marketer_code VARCHAR(100) DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='marketer_commission') THEN
                    ALTER TABLE orders ADD COLUMN marketer_commission REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='payment_method') THEN
                    ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50) DEFAULT 'كاش';
                END IF;
            END $$;
        """)
        
        # إضافة الأعمدة المفقودة إلى products
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='products' AND column_name='commission_egp') THEN
                    ALTER TABLE products ADD COLUMN commission_egp REAL DEFAULT 0;
                END IF;
            END $$;
        """)
        
        # إضافة الأعمدة المفقودة إلى marketers
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='marketers' AND column_name='balance') THEN
                    ALTER TABLE marketers ADD COLUMN balance REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='marketers' AND column_name='total_earned') THEN
                    ALTER TABLE marketers ADD COLUMN total_earned REAL DEFAULT 0;
                END IF;
            END $$;
        """)
        
        # إنشاء جدول withdraw_requests
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY,
                marketer_id INTEGER,
                marketer_code VARCHAR(50),
                amount REAL DEFAULT 0,
                vodafone_number VARCHAR(50),
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database migration completed!")
    except Exception as e:
        print(f"Migration error: {e}")

# تشغيل التحديث عند بدء التشغيل
migrate_database()

# ==========================================
# إنشاء الجداول الأساسية
# ==========================================

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                selling_price REAL DEFAULT 0,
                purchasing_price REAL DEFAULT 0,
                commission_egp REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT,
                extra_images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                marketer_code VARCHAR(100) DEFAULT '',
                marketer_commission REAL DEFAULT 0,
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                payment_method VARCHAR(50) DEFAULT 'كاش',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                code VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                commission_rate REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'admin',
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        hashed = generate_password_hash('MoSebA01065653401')
        cursor.execute("""
            INSERT INTO users (username, password, role, name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
        """, ('admin', hashed, 'manager', 'المدير'))

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized!")
    except Exception as e:
        print(f"Init error: {e}")

init_database()

# ==========================================
# Middleware
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'manager':
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def marketer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'marketer_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

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

@app.route('/marketer_login.html')
def marketer_login_page():
    return render_template('marketer_login.html')

@app.route('/marketer_dashboard.html')
def marketer_dashboard_page():
    return render_template('marketer_dashboard.html')

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
        return jsonify(products)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
@manager_required
def create_product():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO products (name, category, description, selling_price, purchasing_price, commission_egp, stock_quantity, image_url, extra_images)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        """, (
            data.get('name'), data.get('category'), data.get('description'),
            data.get('selling_price', 0), data.get('purchasing_price', 0),
            data.get('commission_egp', 0), data.get('stock_quantity', 0),
            data.get('image_url'), data.get('extra_images', '[]')
        ))
        product = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['PUT'])
@manager_required
def update_product(pid):
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            UPDATE products SET name=%s, category=%s, description=%s, selling_price=%s, 
            purchasing_price=%s, commission_egp=%s, stock_quantity=%s, image_url=%s, extra_images=%s
            WHERE id=%s RETURNING *;
        """, (data.get('name'), data.get('category'), data.get('description'),
            data.get('selling_price', 0), data.get('purchasing_price', 0),
            data.get('commission_egp', 0), data.get('stock_quantity', 0),
            data.get('image_url'), data.get('extra_images', '[]'), pid))
        product = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(product)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['DELETE'])
@manager_required
def delete_product(pid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s;", (pid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API Orders
# ==========================================

@app.route('/api/orders', methods=['GET'])
@login_required
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
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        products_json = json.dumps(data.get('products', []), ensure_ascii=False)
        marketer_code = data.get('marketer_code', '')
        
        # حساب العمولة الإجمالية للمسوق (بالجنيه)
        total_commission = 0
        for product in data.get('products', []):
            cur.execute("SELECT commission_egp FROM products WHERE id = %s;", (product.get('id'),))
            prod = cur.fetchone()
            if prod and prod['commission_egp']:
                total_commission += prod['commission_egp'] * product.get('qty', 1)
        
        cur.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_code, marketer_commission, products_json, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        """, (
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('customer_address'),
            data.get('total_price', 0),
            marketer_code,
            total_commission,
            products_json,
            'كاش'
        ))
        
        order = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "order": order}), 201
    except Exception as e:
        print(f"Order error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders/<int:oid>/status', methods=['PUT'])
@login_required
def update_order_status(oid):
    try:
        data = request.json
        new_status = data.get('status')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM orders WHERE id = %s;", (oid,))
        order = cur.fetchone()
        
        cur.execute("UPDATE orders SET status=%s WHERE id=%s RETURNING *;", (new_status, oid))
        updated_order = cur.fetchone()
        
        # إذا تم التسليم، أضف العمولة للمسوق
        if new_status == 'تم التسليم' and order and order.get('marketer_code') and order.get('marketer_commission', 0) > 0:
            cur.execute("""
                UPDATE marketers 
                SET balance = balance + %s, total_earned = total_earned + %s 
                WHERE code = %s;
            """, (order['marketer_commission'], order['marketer_commission'], order['marketer_code']))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(updated_order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/track', methods=['GET'])
def track_order():
    try:
        phone = request.args.get('phone')
        if not phone:
            return jsonify({"error": "Phone required"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE customer_phone = %s ORDER BY id DESC;", (phone,))
        orders = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API Marketers
# ==========================================

@app.route('/api/marketers', methods=['GET'])
@manager_required
def get_marketers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, phone, code, commission_rate, balance, total_earned FROM marketers ORDER BY id DESC;")
        marketers = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(marketers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketers', methods=['POST'])
@manager_required
def create_marketer():
    try:
        data = request.json
        hashed = generate_password_hash(data.get('password', '123456'))
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO marketers (name, phone, code, password, commission_rate)
            VALUES (%s, %s, %s, %s, %s) RETURNING id, name, phone, code, commission_rate, balance, total_earned;
        """, (data.get('name'), data.get('phone'), data.get('code'), hashed, data.get('commission_rate', 0)))
        marketer = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(marketer), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketers/<int:mid>', methods=['DELETE'])
@manager_required
def delete_marketer(mid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM marketers WHERE id = %s;", (mid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/login', methods=['POST'])
def marketer_login():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM marketers WHERE code = %s;", (data.get('code'),))
        marketer = cur.fetchone()
        cur.close()
        conn.close()
        
        if marketer and check_password_hash(marketer['password'], data.get('password')):
            session['marketer_id'] = marketer['id']
            session['marketer_code'] = marketer['code']
            session['marketer_name'] = marketer['name']
            return jsonify({"success": True, "code": marketer['code'], "name": marketer['name'], "balance": marketer['balance']})
        
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/logout', methods=['POST'])
def marketer_logout():
    session.pop('marketer_id', None)
    session.pop('marketer_code', None)
    session.pop('marketer_name', None)
    return jsonify({"success": True})

@app.route('/api/marketer/check', methods=['GET'])
def check_marketer():
    return jsonify({
        "authenticated": 'marketer_id' in session,
        "code": session.get('marketer_code'),
        "name": session.get('marketer_name')
    })

@app.route('/api/marketer/stats', methods=['GET'])
@marketer_required
def marketer_stats():
    try:
        code = session['marketer_code']
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM orders WHERE marketer_code = %s ORDER BY id DESC;", (code,))
        orders = cur.fetchall()
        
        cur.execute("SELECT * FROM marketers WHERE code = %s;", (code,))
        marketer = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "marketer_name": marketer['name'],
            "marketer_code": marketer['code'],
            "balance": marketer['balance'] or 0,
            "total_earned": marketer['total_earned'] or 0,
            "orders": orders
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/create_order', methods=['POST'])
@marketer_required
def marketer_create_order():
    try:
        data = request.json
        marketer_code = session['marketer_code']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        products_json = json.dumps(data.get('products', []), ensure_ascii=False)
        
        total_commission = 0
        for product in data.get('products', []):
            cur.execute("SELECT commission_egp FROM products WHERE id = %s;", (product.get('id'),))
            prod = cur.fetchone()
            if prod and prod['commission_egp']:
                total_commission += prod['commission_egp'] * product.get('qty', 1)
        
        cur.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_code, marketer_commission, products_json, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
        """, (
            data.get('customer_name'),
            data.get('customer_phone'),
            data.get('customer_address'),
            data.get('total_price', 0),
            marketer_code,
            total_commission,
            products_json,
            'كاش'
        ))
        
        order = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "order": order}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==========================================
# API Withdraw Requests
# ==========================================

@app.route('/api/withdraw/request', methods=['POST'])
@marketer_required
def request_withdraw():
    try:
        data = request.json
        amount = float(data.get('amount', 0))
        vodafone_number = data.get('vodafone_number', '')
        
        if amount <= 0:
            return jsonify({"success": False, "error": "المبلغ غير صحيح"}), 400
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT balance FROM marketers WHERE id = %s;", (session['marketer_id'],))
        marketer = cur.fetchone()
        
        if not marketer or marketer['balance'] < amount:
            cur.close()
            conn.close()
            return jsonify({"success": False, "error": "الرصيد غير كافي"}), 400
        
        cur.execute("""
            INSERT INTO withdraw_requests (marketer_id, marketer_code, amount, vodafone_number, status)
            VALUES (%s, %s, %s, %s, 'قيد المراجعة') RETURNING *;
        """, (session['marketer_id'], session['marketer_code'], amount, vodafone_number))
        
        withdraw_request = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"success": True, "request": withdraw_request}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/withdraw/requests', methods=['GET'])
@manager_required
def get_withdraw_requests():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM withdraw_requests ORDER BY id DESC;")
        requests = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(requests)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/withdraw/requests/<int:rid>', methods=['PUT'])
@manager_required
def process_withdraw_request(rid):
    try:
        data = request.json
        new_status = data.get('status')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM withdraw_requests WHERE id = %s;", (rid,))
        withdraw_request = cur.fetchone()
        
        if not withdraw_request:
            return jsonify({"error": "Request not found"}), 404
        
        if new_status == 'مقبول':
            cur.execute("UPDATE marketers SET balance = balance - %s WHERE id = %s;", 
                       (withdraw_request['amount'], withdraw_request['marketer_id']))
        
        cur.execute("""
            UPDATE withdraw_requests SET status=%s, processed_at=NOW() WHERE id=%s RETURNING *;
        """, (new_status, rid))
        
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify(updated)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API Users
# ==========================================

@app.route('/api/users', methods=['GET'])
@manager_required
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, role, name, created_at FROM users ORDER BY id DESC;")
        users = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['POST'])
@manager_required
def create_user():
    try:
        data = request.json
        hashed = generate_password_hash(data.get('password'))
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO users (username, password, role, name)
            VALUES (%s, %s, %s, %s) RETURNING id, username, role, name;
        """, (data.get('username'), hashed, data.get('role', 'admin'), data.get('name')))
        user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(user), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@manager_required
def delete_user(uid):
    try:
        if uid == session.get('user_id'):
            return jsonify({"error": "Cannot delete yourself"}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s;", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API Auth
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s;", (data.get('username'),))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password'], data.get('password')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            return jsonify({"success": True, "role": user['role'], "name": user['name']})
        
        return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
@login_required
def dashboard_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total_sales FROM orders;")
        total_sales = cur.fetchone()['total_sales']
        
        cur.execute("SELECT COUNT(*) as total_orders FROM orders;")
        total_orders = cur.fetchone()['total_orders']
        
        cur.execute("SELECT COUNT(*) as total_products FROM products;")
        total_products = cur.fetchone()['total_products']
        
        cur.execute("SELECT COUNT(*) as total_marketers FROM marketers;")
        total_marketers = cur.fetchone()['total_marketers']
        
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM orders GROUP BY status;
        """)
        orders_by_status = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "total_sales": total_sales,
            "total_orders": total_orders,
            "total_products": total_products,
            "total_marketers": total_marketers,
            "orders_by_status": orders_by_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
