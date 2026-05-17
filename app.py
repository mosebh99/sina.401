import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))\nTEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)

DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

# 🚀 دالة الإصلاح والهيكلة الفورية لقاعدة البيانات (تحديث الجداول آلياً)
def fix_database_and_create_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. تحديث جدول المنتجات بالحقول المحاسبية وصيغ الصور الإضافية المعقدة
        cursor.execute('''
            ALTER TABLE products ADD COLUMN IF NOT EXISTS purchasing_price REAL DEFAULT 0;
            ALTER TABLE products ADD COLUMN IF NOT EXISTS commission REAL DEFAULT 0;
            ALTER TABLE products ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 0;
            ALTER TABLE products ADD COLUMN IF NOT EXISTS extra_images TEXT DEFAULT '[]';
        ''')
        
        # 2. إنشاء جدول المسوقين المحمي وطلبات الانضمام الأمنية
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                marketer_code VARCHAR(100) UNIQUE DEFAULT NULL,
                status VARCHAR(50) DEFAULT 'معلق'
            );
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()
        print("🎉 [SYSTEM SATELLITE] Database structured and verified successfully!")
    except Exception as e:
        print(f"❌ Database structure failed: {e}")

# تشغيل الفحص الهيكلي فوراً عند الإقلاع
fix_database_and_create_tables()

# --- 🌐 مسارات توجيه واستعراض صفحات الـ Frontend ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index.html')
def index_redirect():
    return render_template('index.html')

@app.route('/cashier.html')
def cashier():
    return render_template('cashier.html')

@app.route('/login.html')
def login():
    return render_template('login.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    return render_template('product_detail.html')


# --- 📦 مسارات الـ API والتحكم البرمجي للمنتجات والمخزن ---

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/products/<int:id>', methods=['GET'])
def get_single_product(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM products WHERE id = %s", (id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return jsonify(row), 200
        return jsonify({"status": "error", "message": "Product not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json() or {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (name, category, description, image_url, extra_images, purchasing_price, selling_price, commission, stock_quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'),
            data.get('category', 'عام'),
            data.get('description', ''),
            data.get('image_url'), # استقبال نص الصورة الرئيسية المضغوطة
            data.get('extra_images', '[]'), # استقبال مصفوفة الصور الإضافية المعقدة
            float(data.get('purchasing_price', 0)),
            float(data.get('selling_price', 0)),
            float(data.get('commission', 0)),
            int(data.get('stock_quantity', 0))
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# --- 🔐 مسارات التحقق والأمان والـ Auth وبوابة العبور ---

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # 1. الدخول الافتراضي للمشرف (إبراهيم) لوحة التحكم الكبرى
    if username == "admin" and password == "MoSebA01065653401":
        return jsonify({"status": "success", "redirect": "/cashier.html"}), 200
        
    # 2. فحص ما إذا كان المسجل هو مسوق مقبول ومثبت بكود في قاعدة البيانات
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM marketers WHERE (marketer_code = %s OR phone = %s) AND password = %s", (username, username, password))
        marketer = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if marketer:
            if marketer['status'] == 'معلق':
                return jsonify({"status": "error", "message": "حسابك معلق حالياً بانتظار تفعيل ومراجعة الإدارة العليا (إبراهيم)"}), 403
            # إذا كان مقبولاً، يتم توجيهه تلقائياً للوحة أرباح المسوقين الخاصة به
            return jsonify({"status": "success", "redirect": f"/marketers.html?code={marketer['marketer_code']}"}), 200
            
        return jsonify({"status": "error", "message": "بيانات العبور السرية خاطئة!"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ⏳ مسارات التحكم بحسابات وطلبات انضمام المسوقين الجدد ---

@app.route('/api/marketers/apply', methods=['POST'])
def apply_marketer():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    password = data.get('password', '').strip()
    
    if not name or not phone or not password:
        return jsonify({"status": "error", "message": "برجاء استكمال كافة الحقول المطلوبة!"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO marketers (name, phone, password, status)
            VALUES (%s, %s, %s, 'معلق')
        ''', (name, phone, password))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success", "message": "تم تقديم طلبك بنجاح"}), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"status": "error", "message": "رقم الهاتف هذا تقدم بطلب انضمام سابقاً!"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/marketers/pending', methods=['GET'])
def get_pending_marketers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, phone, status FROM marketers WHERE status = 'معلق' ORDER BY id DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/marketers/approve/<int:id>', methods=['POST'])
def approve_marketer(id):
    data = request.get_json() or {}
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({"status": "error", "message": "برجاء تخصيص كود تسويقي فريد للمسوق أولاً!"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE marketers 
            SET status = 'مقبول', marketer_code = %s 
            WHERE id = %s
        ''', (code, id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except psycopg2.errors.UniqueViolation:
        return jsonify({"status": "error", "message": "كود التسويق هذا مخصص لمسوق آخر بالفعل، اختر كوداً فريداً!"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- 📦 واجهات ومسارات معالجة طلبات المبيعات والشحنات العامة ---

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
            data.get('customer_phone'), \n            data.get('customer_address'), 
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
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/public/orders', methods=['GET'])
def get_public_orders():
    return get_orders()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
