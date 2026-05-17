import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for, session

# ضبط مسار المجلد الرئيسي مباشرة لـ Vercel
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=BASE_DIR, static_folder=BASE_DIR)

app.secret_key = os.environ.get('FLASK_SECRET_KEY') or "SinaaStoreSuperSecretKey2026_JWT"
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

# إعدادات رفع الصور محلياً
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 🌐 مسارات العرض والتوجيه الفوري لملفاتك ---

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

# --- 🔑 نظام الحسابات (Auth APIs) ---

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

# --- 📸 نظام رفع الصور ---
@app.route('/api/upload', methods=['POST'])
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
            uploaded_urls.append(f"/uploads/{filename}")
            
    return jsonify({"status": "success", "urls": uploaded_urls}), 200

# --- 🛒 واجهات الـ API المحدثة بالكامل للمنتجات ---

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
        cursor.execute('''
            INSERT INTO products (name, category, selling_price, purchasing_price, commission, stock_quantity, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data.get('name'), data.get('category', 'عام'), 
            float(data.get('selling_price', 0)), float(data.get('purchasing_price', 0)),
            float(data.get('commission', 0)), int(data.get('stock_quantity', 0)),
            data.get('image_url'), data.get('description', '')
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

@app.route('/api/orders/<int:o_id>', methods=['PUT'])
def update_order_status(o_id):
    data = request.get_json() or {}
    status = data.get('status')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, o_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e: 
        return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
