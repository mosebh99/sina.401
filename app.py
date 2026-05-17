import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for, session

# 🎯 ضبط المسارات الديناميكية لضمان قراءة المجلدات داخل بيئة Vercel Serverless
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(BASE_DIR, 'templates')
static_dir = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# 🛡️ إعدادات الأمان والتشفير عبر الـ Environment Variables لمنع تسريب البيانات
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or "SinaaStoreSuperSecretKey2026_JWT"
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

# إعدادات رفع الصور
UPLOAD_FOLDER = os.path.join(static_dir, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. جدول المنتجات
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
                images_json TEXT DEFAULT '[]', 
                description TEXT,
                is_featured BOOLEAN DEFAULT FALSE,
                discount_price REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. جدول الطلبات
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
                coupon_used TEXT,
                payment_method TEXT DEFAULT 'الدفع عند الاستلام',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. جدول حسابات الأدمن
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        
        cursor.execute("SELECT * FROM admins WHERE username='admin'")
        if not cursor.fetchone():
            hashed = generate_password_hash("SinaaAdmin2026")
            cursor.execute("INSERT INTO admins (username, password_hash) VALUES ('admin', %s)", (hashed,))

        conn.commit()
        cursor.close()
        conn.close()
        print("🚀 Database connected and initialized successfully!")
    except Exception as e:
        print("❌ Database Connection/Init Error:", e)

# تشغيل فحص قاعدة البيانات عند بدء السيرفر
init_db()

# 🔐 Decorators لحماية الصفحات
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def api_admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"status": "error", "message": "غير مصرح بالدخول للوحة التحكم."}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# --- 🌐 مسارات العرض (Templates Routes) ---

@app.route('/')
def index():
    # التأكد من وجود الملف لتجنب أخطاء الفتح في Vercel
    if not os.path.exists(os.path.join(template_dir, 'index.html')):
        return "❌ خطأ في النظام: لم يتم العثور على ملفات الواجهة داخل مجلد templates.", 500
    return render_template('index.html')

@app.route('/index.html')
def index_html():
    return redirect(url_for('index'))

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/cashier.html')
@admin_required
def cashier():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    return render_template('product_detail.html', product_id=product_id)

# --- 🔑 مسارات نظام الحسابات (Auth APIs) ---

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if admin and check_password_hash(admin['password_hash'], password):
            session['is_admin'] = True
            session['username'] = username
            return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح"}), 200
        return jsonify({"status": "error", "message": "بيانات الدخول غير صحيحة"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": "فشل الاتصال بقاعدة البيانات"}), 500

@app.route('/api/auth/logout')
def api_logout():
    session.clear()
    return redirect(url_for('index'))

# --- 📸 نظام رفع الصور المتعددة الحقيقي ---
@app.route('/api/upload', methods=['POST'])
@api_admin_required
def upload_images():
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "لا توجد ملفات مرفوعة"}), 400
    
    files = request.files.getlist('files')
    uploaded_urls = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_urls.append(f"/static/uploads/{filename}")
            
    return jsonify({"status": "success", "urls": uploaded_urls}), 200

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

@app.route('/api/products/<int:p_id>', methods=['GET'])
def get_single_product(p_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM products WHERE id=%s", (p_id,))
        prod = cursor.fetchone()
        cursor.close()
        conn.close()
        if prod:
            return jsonify(dict(prod)), 200
        return jsonify({"status": "error", "message": "المنتج غير موجود"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/products', methods=['POST'])
@api_admin_required
def add_product():
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, images_json, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'), data.get('category', 'عام'), 
            float(data.get('selling_price', 0)), float(data.get('purchasing_price', 0)),
            float(data.get('commission', 0)), int(data.get('stock_quantity', 0)),
            data.get('image_url'), json.dumps(data.get('images_json', [])), data.get('description', '')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['DELETE'])
@api_admin_required
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
        products_json_str = json.dumps(data['products'], ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (data['customer_name'], data['customer_phone'], data['customer_address'], float(data['total_price']), data.get('marketer_id'), products_json_str))
        
        for item in data['products']:
            cursor.execute("UPDATE products SET stock_quantity = GREATEST(0, stock_quantity - %s) WHERE name = %s", (int(item.get('qty', 1)), item.get('name')))
            
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/orders', methods=['GET'])
@api_admin_required
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
@api_admin_required
def update_order_status(o_id):
    data = request.get_json() or {}
    status = data.get('status', 'قيد المراجعة')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s", (status, o_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e: 
        return jsonify({"status": "error"}), 500

@app.route('/api/public/orders')
def get_public_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, customer_phone, status, total_price, products_json, marketer_id FROM orders ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        return jsonify([]), 200

if __name__ == '__main__':
    app.run(debug=True)
