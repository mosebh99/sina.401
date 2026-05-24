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
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. جدول المنتجات (الهواتف والأجهزة الذكية)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'هواتف ذكية',
                selling_price INT NOT NULL,
                commission INT DEFAULT 0,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. جدول المسوقين (مع ميزة القبول المبدئي FALSE)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT,
                is_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. جدول الطلبات الكامل
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_address TEXT NOT NULL,
                total_price INT NOT NULL,
                products JSONB,
                marketer_code TEXT,
                status TEXT DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. جدول سحب الأرباح للمسوقين
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                marketer_code TEXT NOT NULL,
                amount INT NOT NULL,
                status TEXT DEFAULT 'قيد الانتظار',
                payment_method TEXT,
                wallet_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. جدول إدارة المستخدمين (الأدمن / الكاشير)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'cashier'
            );
        """)
        
        # إنشاء حساب الأدمن الافتراضي لو مش موجود
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin';")
        if cursor.fetchone()[0] == 0:
            hashed_pass = generate_password_hash('sina401admin')
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', %s, 'admin');", (hashed_pass,))

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ تم تهيئة قاعدة بيانات سينا ستور 401 بنجاح كامل.")
    except Exception as e:
        print("❌ خطأ أثناء تهيئة قاعدة البيانات:", str(e))

init_database()

# دالة حماية مسارات الإدارة (Middleware)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# مسارات عرض واجهات صفحات الـ HTML
# ==========================================
@app.route('/')
def home(): return render_template('index.html')

@app.route('/index.html')
def index(): return render_template('index.html')

@app.route('/product_detail.html')
def detail(): return render_template('product_detail.html')

@app.route('/marketer_login.html')
def m_login(): return render_template('marketer_login.html')

@app.route('/login.html')
def login_admin_page(): return render_template('login.html')

@app.route('/marketer_dashboard.html')
def m_dash():
    if 'marketer_code' not in session:
        return redirect('/marketer_login.html')
    return render_template('marketer_dashboard.html')

@app.route('/cashier.html')
@login_required
def cashier(): return render_template('cashier.html')

# ==========================================
# APIs التحكم بالمنتجات
# ==========================================
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id DESC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:p_id>', methods=['GET'])
def get_product(p_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products WHERE id = %s;", (p_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(row) if row else (jsonify({"error": "المنتج غير موجود"}), 404)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO products (name, category, selling_price, commission, image_url)
            VALUES (%s, %s, %s, %s, %s) RETURNING *;
        """, (data['name'], data.get('category', 'هواتف ذكية'), int(data['selling_price']), int(data.get('commission', 0)), data.get('image_url', '')))
        p = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(p), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# APIs التحكم بالطلبات والمبيعات
# ==========================================
@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, products, marketer_code)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """, (data['customer_name'], data['customer_phone'], data['customer_address'], int(data['total_price']), json.dumps(data['products']), data.get('marketer_code')))
        oid = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "order_id": oid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM orders ORDER BY id DESC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:o_id>', methods=['PUT'])
@login_required
def update_order_status(o_id):
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = %s WHERE id = %s;", (data['status'], o_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/track', methods=['GET'])
def track_order():
    oid = request.args.get('id')
    if not oid: return jsonify({"error": "معرف الطلب مطلوب"}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, status, total_price, created_at, marketer_code FROM orders WHERE id = %s;", (int(oid),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(row) if row else (jsonify({"error": "الطلب غير مسجل"}), 404)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# APIs إدارة وقبول المسوقين الجدد
# ==========================================
@app.route('/api/marketers', methods=['GET'])
@login_required
def get_all_marketers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, code, phone, is_approved, created_at FROM marketers ORDER BY id DESC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketers/approve/<int:m_id>', methods=['POST'])
@login_required
def approve_marketer(m_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE marketers SET is_approved = TRUE WHERE id = %s;", (m_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "تم تفعيل حساب المسوق بنجاح"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/register', methods=['POST'])
def register_marketer():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM marketers WHERE code = %s;", (data['code'],))
        if cur.fetchone()[0] > 0:
            return jsonify({"success": False, "message": "كود المسوق مستخدم بالفعل، يرجى اختيار كود آخر"}), 400
        
        cur.execute("""
            INSERT INTO marketers (name, code, password, phone, is_approved)
            VALUES (%s, %s, %s, %s, FALSE);
        """, (data['name'], data['code'], data['password'], data['phone']))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "تم تقديم طلبك بنجاح، في انتظار تفعيل الإدارة لحسابك."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/login', methods=['POST'])
def affiliate_login():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM marketers WHERE code = %s;", (data['code'],))
        m = cur.fetchone()
        cur.close()
        conn.close()
        
        if m and m['password'] == data['password']:
            if not m['is_approved']:
                return jsonify({"success": False, "message": "❌ حسابك لم يتم تفعيله من الإدارة بعد. يرجى التواصل مع الدعم."}), 403
            session['marketer_id'] = m['id']
            session['marketer_code'] = m['code']
            session['marketer_name'] = m['name']
            return jsonify({"success": True, "message": "أهلاً بك في لوحة التحكم"})
        return jsonify({"success": False, "message": "كود المسوق أو كلمة المرور خاطئة"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/logout', methods=['POST'])
def affiliate_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/marketer/stats', methods=['GET'])
def get_marketer_stats():
    if 'marketer_code' not in session: return jsonify({"error": "غير مصرح"}), 401
    m_code = session['marketer_code']
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, customer_name, total_price, status, created_at, products FROM orders WHERE marketer_code = %s ORDER BY id DESC;", (m_code,))
        orders = cur.fetchall()
        
        total_balance = 0
        pending_balance = 0
        for o in orders:
            try:
                prods = json.loads(o['products']) if isinstance(o['products'], str) else o['products']
            except:
                prods = []
            for p in prods:
                cur.execute("SELECT commission FROM products WHERE id = %s;", (p.get('id'),))
                p_info = cur.fetchone()
                comm = p_info['commission'] if p_info else 0
                if o['status'] == 'تم التسليم': 
                    total_balance += comm
                elif o['status'] in ['قيد المراجعة', 'جاري الشحن']: 
                    pending_balance += comm

        cur.execute("SELECT COALESCE(SUM(amount), 0) as paid FROM withdrawals WHERE marketer_code = %s AND status = 'مقبول';", (m_code,))
        paid = cur.fetchone()['paid']
        cur.close()
        conn.close()
        
        return jsonify({
            "marketer_name": session['marketer_name'], 
            "marketer_code": m_code,
            "total_balance": total_balance, 
            "pending_balance": pending_balance,
            "available_balance": max(0, total_balance - paid), 
            "paid_amount": paid, 
            "orders": orders
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# التحكم الإداري وتسجيل دخول الموظفين
# ==========================================
@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s;", (data['username'],))
        u = cur.fetchone()
        cur.close()
        conn.close()
        if u and (check_password_hash(u['password'], data['password']) or u['password'] == data['password']):
            session['user_id'] = u['id']
            session['username'] = u['username']
            session['role'] = u['role']
            return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح"})
        return jsonify({"success": False, "message": "بيانات الدخول الإدارية خاطئة"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/stats/dashboard', methods=['GET'])
@login_required
def dashboard_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total_sales FROM orders;")
        sales = cur.fetchone()['total_sales']
        cur.execute("SELECT COUNT(*) as c FROM orders;"); o_cnt = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM products;"); p_cnt = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM marketers;"); m_cnt = cur.fetchone()['c']
        cur.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status;")
        statuses = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"total_sales": sales, "total_orders": o_cnt, "total_products": p_cnt, "total_marketers": m_cnt, "orders_by_status": statuses})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 5000)))
