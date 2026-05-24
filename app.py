import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, session
from whitenoise import WhiteNoise
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# تحميل الإعدادات من ملف .env
load_dotenv()

app = Flask(__name__)
# استخدام WhiteNoise لخدمة الملفات الثابتة
app.wsgi_app = WhiteNoise(app.wsgi_app, root='static', prefix='static/')

# إعدادات الأمان
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-me')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("Database URL not configured")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# حماية المسارات
def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'manager':
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ==========================================
# المسارات الأساسية
# ==========================================

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# API المنتجات
# ==========================================

@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM products ORDER BY id DESC;")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
@manager_required
def add_product():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (name, price, category, description, image_url) 
        VALUES (%s, %s, %s, %s, %s) RETURNING id;
    """, (data['name'], data['price'], data.get('category'), data.get('description'), data.get('image_url')))
    pid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": pid, "message": "Product added"})

# ==========================================
# API الطلبات
# ==========================================

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, products_json, status)
        VALUES (%s, %s, %s, %s, %s, 'قيد المراجعة');
    """, (data['name'], data['phone'], data['address'], data['total'], json.dumps(data['products'])))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True})

# ==========================================
# API تسجيل الدخول
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    # يفضل مقارنة الهاش وليس النص الصريح
    if data.get('username') == 'admin' and data.get('password') == os.environ.get('ADMIN_PASSWORD'):
        session['user_id'] = 1
        session['role'] = 'manager'
        return jsonify({"success": True, "role": "manager"})
    return jsonify({"success": False, "message": "بيانات خاطئة"}), 401

if __name__ == '__main__':
    app.run(debug=True)
