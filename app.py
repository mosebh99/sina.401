import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, abort

app = Flask(__name__, template_folder='templates', static_folder='static')

# 🛡️ إعدادات الأمان والتشفير عبر Environment Variables
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or "SinaaStoreSuperSecretKey2026_JWT"
DATABASE_URL = os.environ.get('DATABASE_URL')

# إعدادات رفع الصور
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("❌ خطأ: لم يتم ضبط متغير البيئة DATABASE_URL")
    return psycopg2.connect(DATABASE_URL)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. جدول المنتجات المطور
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
    
    # 2. جدول الطلبات المطور
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
    
    # 3. جدول الكوبونات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            discount_percent REAL NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. حساب الأدمن الافتراضي (إذا لم يكن موجوداً)
    # اليوزر الافتراضي: admin | الباسورد الافتراضية: SinaaAdmin2026
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

try:
    init_db()
except Exception as e:
    print("Database Initialization Info/Error:", e)

# 🔐 Decorator لحماية مسارات الأدمن (ريديركت لصفحة تسجيل الدخول)
def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# 🔐 Decorator لحماية الـ APIs (إرجاع خطأ 401 غير مصرح)
def api_admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({"status": "error", "message": "غير مصرح لك بالوصول. يرجى تسجيل الدخول أولاً."}), 401
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# --- 🌐 مسارات صفحات الـ Templates ---

@app.route('/')
def index():
    return render_template('index.html')

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

# --- 🔑 مسارات نظام الحسابات وتسجيل الدخول ---

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
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
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/auth/logout', methods=['GET', 'POST'])
def api_logout():
    session.clear()
    return redirect(url_for('index'))

# --- 📸 مسار رفع الصور المتعددة الحقيقي ---
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
            # مسار الصورة للفرونت إند
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
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, images_json, description, is_featured, discount_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'), data.get('category', 'عام'), 
            float(data.get('selling_price', 0)), float(data.get('purchasing_price', 0)),
            float(data.get('commission', 0)), int(data.get('stock_quantity', 0)),
            data.get('image_url'), json.dumps(data.get('images_json', [])), data.get('description', ''),
            data.get('is_featured', False), float(data.get('discount_price', 0))
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:p_id>', methods=['PUT'])
@api_admin_required
def update_product(p_id):
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=%s, category=%s, selling_price=%s, purchasing_price=%s, commission=%s, stock_quantity=%s, image_url=%s, images_json=%s, description=%s, is_featured=%s, discount_price=%s, updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
        ''', (
            data.get('name'), data.get('category'), float(data.get('selling_price')), 
            float(data.get('purchasing_price')), float(data.get('commission')), int(data.get('stock_quantity')),
            data.get('image_url'), json.dumps(data.get('images_json', [])), data.get('description'),
            data.get('is_featured', False), float(data.get('discount_price', 0)), p_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
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

# --- 📦 واجهات الـ API الخاصة بالطلبات والكوبونات ---

@app.route('/api/coupons/validate', methods=['POST'])
def validate_coupon():
    code = request.get_json().get('code', '').strip().upper()
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM coupons WHERE code=%s AND is_active=TRUE", (code,))
        coupon = cursor.fetchone()
        cursor.close()
        conn.close()
        if coupon: 
            return jsonify({"status": "valid", "discount_percent": coupon['discount_percent']}), 200
        return jsonify({"status": "invalid"}), 404
    except: 
        return jsonify({"status": "invalid"}), 404

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        products_json_str = json.dumps(data['products'], ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json, coupon_used, payment_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['customer_name'], data['customer_phone'], data['customer_address'], float(data['total_price']), data.get('marketer_id'), products_json_str, data.get('coupon_used'), data.get('payment_method', 'الدفع عند الاستلام')))
        
        # إدارة المخزون: خصم الكميات المباعة أوتوماتيكياً
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
    except: 
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
    # API عام غير محمي ومفلتر ومحدد الحقول من أجل تتبع الطلبات بدون تسريب بيانات حساسة
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, customer_phone, status, total_price, products_json, marketer_id FROM orders ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(r) for r in rows]), 200
    except:
        return jsonify([]), 200

# صفحة الخطأ 404 الاحترافية الموجهة للرئيسية
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
