import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session
from whitenoise import WhiteNoise
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2024')

# رابط الاتصال بقاعدة بيانات Supabase
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    """إنشاء اتصال مؤمن بالسيرفر السحابي"""
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

# دالة الإصلاح التلقائي لقاعدة البيانات
def fix_database_columns_forced():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # جدول المنتجات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                selling_price REAL DEFAULT 0,
                purchasing_price REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT,
                extra_images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # جدول الطلبات
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                marketer_id VARCHAR(100),
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # جدول المسوقين
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                code VARCHAR(50) UNIQUE NOT NULL,
                commission_rate REAL DEFAULT 0,
                total_sales REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database error: {e}")

fix_database_columns_forced()

# ==========================================
# نظام التحقق من تسجيل الدخول
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# مسارات واجهات العرض
# ==========================================

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/cashier.html')
@login_required
def cashier_page():
    return render_template('cashier.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/marketers.html')
def marketers_page():
    return render_template('marketers.html')

@app.route('/product_detail.html')
def product_detail_page():
    return render_template('product_detail.html')

# ==========================================
# API تسجيل الدخول
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if username == "admin" and password == os.environ.get('ADMIN_PASSWORD', 'MoSebA01065653401'):
        session['admin_logged_in'] = True
        return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح"})

    return jsonify({"success": False, "message": "بيانات الدخول غير صحيحة"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.pop('admin_logged_in', None)
    return jsonify({"success": True, "message": "تم تسجيل الخروج"})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    return jsonify({"authenticated": 'admin_logged_in' in session})

# ==========================================
# واجهات المنتجات
# ==========================================

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    try:
        conn = get_db_connection()
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM products ORDER BY id DESC;")
            products = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(products)

        elif request.method == 'POST':
            data = request.json
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO products (name, category, description, selling_price, purchasing_price, commission, stock_quantity, image_url, extra_images)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                data.get('selling_price', 0), data.get('purchasing_price', 0),
                data.get('commission', 0), data.get('stock_quantity', 0), 
                data.get('image_url'), data.get('extra_images', '[]')
            ))
            new_product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def product_detail(pid):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if request.method == 'GET':
            cur.execute("SELECT * FROM products WHERE id = %s;", (pid,))
            product = cur.fetchone()
            cur.close()
            conn.close()
            if product:
                return jsonify(product)
            return jsonify({"error": "Product not found"}), 404

        elif request.method == 'PUT':
            data = request.json
            cur.execute("""
                UPDATE products SET 
                    name = %s, category = %s, description = %s,
                    selling_price = %s, purchasing_price = %s,
                    commission = %s, stock_quantity = %s,
                    image_url = %s, extra_images = %s
                WHERE id = %s RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                data.get('selling_price', 0), data.get('purchasing_price', 0),
                data.get('commission', 0), data.get('stock_quantity', 0),
                data.get('image_url'), data.get('extra_images', '[]'), pid
            ))
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(updated)

        elif request.method == 'DELETE':
            cur.execute("DELETE FROM products WHERE id = %s;", (pid,))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# واجهات الطلبات
# ==========================================

@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    try:
        conn = get_db_connection()
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM orders ORDER BY id DESC;")
            orders = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(orders)

        elif request.method == 'POST':
            data = request.json
            cur = conn.cursor(cursor_factory=RealDictCursor)

            items_data = data.get('products') or data.get('items') or []
            products_json_str = json.dumps(items_data, ensure_ascii=False)
            total_val = data.get('total_price') or data.get('total_val') or 0

            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('customer_name'), data.get('customer_phone'), data.get('customer_address'),
                float(total_val), data.get('marketer_id'), products_json_str,
                data.get('status', 'قيد المراجعة')
            ))
            new_order = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_order), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:oid>', methods=['GET', 'PUT', 'DELETE'])
def order_detail(oid):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if request.method == 'GET':
            cur.execute("SELECT * FROM orders WHERE id = %s;", (oid,))
            order = cur.fetchone()
            cur.close()
            conn.close()
            if order:
                return jsonify(order)
            return jsonify({"error": "Order not found"}), 404

        elif request.method == 'PUT':
            data = request.json
            cur.execute("""
                UPDATE orders SET status = %s WHERE id = %s RETURNING *;
            """, (data.get('status'), oid))
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(updated)

        elif request.method == 'DELETE':
            cur.execute("DELETE FROM orders WHERE id = %s;", (oid,))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# واجهات المسوقين
# ==========================================

@app.route('/api/marketers', methods=['GET', 'POST'])
def api_marketers():
    try:
        conn = get_db_connection()
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM marketers ORDER BY id DESC;")
            marketers = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(marketers)

        elif request.method == 'POST':
            data = request.json
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO marketers (name, phone, code, commission_rate)
                VALUES (%s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('phone'), data.get('code'),
                data.get('commission_rate', 0)
            ))
            new_marketer = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_marketer), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketers/<int:mid>', methods=['DELETE'])
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

@app.route('/api/marketers/stats/<code>', methods=['GET'])
def marketer_stats(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT COUNT(*) as total_orders, COALESCE(SUM(total_price), 0) as total_sales
            FROM orders WHERE marketer_id = %s;
        """, (code,))
        stats = cur.fetchone()

        cur.execute("""
            SELECT * FROM orders WHERE marketer_id = %s ORDER BY id DESC;
        """, (code,))
        orders = cur.fetchall()

        cur.close()
        conn.close()
        return jsonify({"stats": stats, "orders": orders})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# لوحة الإحصائيات
# ==========================================

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
    app.run(debug=True)
