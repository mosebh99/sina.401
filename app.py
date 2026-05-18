import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = "sina_store_401_ultra_secret_key_encryption"

DATABASE_URL = "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='allow', cursor_factory=RealDictCursor)

# 🚀 الفحص التلقائي الشامل وبناء الجداول السحابية لمنع سقوط السستم
def init_database_schema():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. جدول المستخدمين (أدمن + مسوقين)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                fullname TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                phone TEXT,
                address TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'marketer',
                status TEXT NOT NULL DEFAULT 'pending',
                marketer_code TEXT UNIQUE
            );
        ''')
        
        # 2. جدول المنتجات الشامل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'عام',
                purchasing_price REAL DEFAULT 0,
                selling_price REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT,
                description TEXT
            );
        ''')
        
        # 3. جدول الطلبات الموحد
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                marketer_id TEXT,
                products_json TEXT,
                status TEXT DEFAULT 'قيد المراجعة'
            );
        ''')
        
        # 4. زرع حساب الأدمن الافتراضي (إبراهيم) لو لم يكن موجوداً
        cursor.execute("SELECT * FROM users WHERE username = 'admin';")
        if not cursor.fetchone():
            hashed_pass = generate_password_hash("admin401")
            cursor.execute("""
                INSERT INTO users (fullname, username, password_hash, role, status)
                VALUES ('إبراهيم السيناوي (المدير)', 'admin', %s, 'admin', 'approved');
            """, (hashed_pass,))
            
        conn.commit()
        cursor.close()
        conn.close()
        print("📊 [Supabase] Database Schema Initialized & Secured Successfully!")
    except Exception as e:
        print(f"❌ Database Initialization Error: {e}")

init_database_schema()

# ==========================================
# 🌐 مسارات الصفحات (Frontend Views)
# ==========================================
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/product_detail.html')
def product_detail_page():
    return render_template('product_detail.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/marketers.html')
def marketers_page():
    if 'user' not in session or session['user']['role'] != 'marketer':
        return redirect(url_for('login_page'))
    return render_template('marketers.html')

@app.route('/cashier.html')
def cashier_page():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login_page'))
    return render_template('cashier.html')

# ==========================================
# 🔐 بوابات التحكم والـ APIs (Backend JSON)
# ==========================================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.json or {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        hashed_p = generate_password_hash(data.get('password'))
        cur.execute("""
            INSERT INTO users (fullname, username, phone, address, password_hash, role, status)
            VALUES (%s, %s, %s, %s, %s, 'marketer', 'pending') RETURNING id;
        """, (data.get('fullname'), data.get('username').strip().lower(), data.get('phone'), data.get('address'), hashed_p))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True, "message": "تم تقديم طلبك بنجاح وفي انتظار موافقة الأدمن لمنحك الكود!"}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "اسم المستخدم هذا محجوز مسبقاً، اختر اسماً آخر"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username').strip().lower()
    password = data.get('password')
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            if user['role'] == 'marketer' and user['status'] != 'approved':
                return jsonify({"error": "حسابك قيد المراجعة حالياً. سيقوم الأدمن بتفعيل حسابك وتوليد كودك قريباً."}), 403
            
            session['user'] = {
                "id": user['id'],
                "fullname": user['fullname'],
                "username": user['username'],
                "role": user['role'],
                "marketer_code": user['marketer_code']
            }
            return jsonify({"success": True, "role": user['role'], "redirect": "/cashier.html" if user['role'] == 'admin' else "/marketers.html"})
        return jsonify({"error": "خطأ في اسم المستخدم أو كلمة المرور السحرية"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout')
def api_logout():
    session.pop('user', None)
    return redirect(url_for('index_page'))

@app.route('/api/auth/session')
def api_session():
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify(None)

# --- إدارة طلبات التفعيل للأدمن ---
@app.route('/api/admin/pending_marketers', methods=['GET', 'POST'])
def admin_marketers():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({"error": "غير مصرح لك"}), 403
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT id, fullname, username, phone, address, status, marketer_code FROM users WHERE role='marketer' ORDER BY id DESC;")
            res = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(res)
        elif request.method == 'POST':
            data = request.json
            uid = data.get('user_id')
            m_code = data.get('marketer_code').strip()
            cur.execute("UPDATE users SET status='approved', marketer_code=%s WHERE id=%s;", (m_code, uid))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- المنتجات ---
@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT * FROM products ORDER BY id DESC;")
            prods = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(prods)
        elif request.method == 'POST':
            if 'user' not in session or session['user']['role'] != 'admin':
                return jsonify({"error": "غير مصرح"}), 403
            data = request.json
            cur.execute("""
                INSERT INTO products (name, category, purchasing_price, selling_price, commission, stock_quantity, image_url, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (data.get('name'), data.get('category'), float(data.get('purchasing_price', 0)), 
                  float(data.get('selling_price', 0)), float(data.get('commission', 0)), 
                  int(data.get('stock_quantity', 0)), data.get('image_url'), data.get('description')))
            new_p = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_p), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    if 'user' not in session or session['user']['role'] != 'admin': return jsonify({"error":"No"}), 403
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = %s;", (pid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error":str(e)}), 500

# --- الطلبات ---
@app.route('/api/orders', methods=['GET', 'POST'])
def api_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT * FROM orders ORDER BY id DESC;")
            orders = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(orders)
        elif request.method == 'POST':
            data = request.json or {}
            total_val = data.get('total_price') or data.get('total_val') or 0
            products_list = data.get('items') or data.get('products') or []
            
            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (data.get('customer_name'), data.get('customer_phone'), data.get('customer_address'),
                  float(total_val), data.get('marketer_id'), json.dumps(products_list, ensure_ascii=False), 'قيد المراجعة'))
            new_order = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_order), 201
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:oid>', methods=['PUT'])
def update_order_status(oid):
    if 'user' not in session or session['user']['role'] != 'admin': return jsonify({"error":"No"}), 403
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = %s WHERE id = %s;", (data.get('status'), oid))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500
