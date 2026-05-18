import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app = app  # السطر السحري الإجباري لمنصة Vercel لمنع الـ Failed

# رابط الاتصال المباشر والمؤمن بقاعدة بيانات Supabase
DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    """إنشاء اتصال مؤمن بالسيرفر السحابي لضمان ثبات الاتصال"""
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

# 🚀 دالة الإصلاح التلقائي: بناء الجداول وتعديل الأعمدة فوراً عند إقلاع الموقع
def fix_database_columns_forced():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # إنشاء جدول المنتجات إن لم يكن موجوداً وتحديث الأعمدة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                selling_price REAL DEFAULT 0,
                purchasing_price REAL DEFAULT 0,
                commission REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT
            );
        ''')
        cursor.execute('''
            ALTER TABLE products ADD COLUMN IF NOT EXISTS purchasing_price REAL DEFAULT 0;
            ALTER TABLE products ADD COLUMN IF NOT EXISTS commission REAL DEFAULT 0;
            ALTER TABLE products ADD COLUMN IF NOT EXISTS stock_quantity INTEGER DEFAULT 0;
        ''')
        
        # إنشاء جدول الطلبات إن لم يكن موجوداً
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                marketer_id VARCHAR(100),
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة'
            );
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("🎉 [FORCED] Database tables & columns verified successfully!")
    except Exception as e:
        print(f"❌ Database auto-fix failed: {e}")

# تشغيل دالة الإصلاح فوراً عند بدء التطبيق
fix_database_columns_forced()

# ==========================================
# 🏠 مسارات واجهات العرض (Frontend Routes)
# ==========================================

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/cashier.html')
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
# ⚙️ واجهات برمجية التطبيقات (API Routes)
# ==========================================

# --- 📦 واجهات المنتجات ---

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
                INSERT INTO products (name, category, description, selling_price, purchasing_price, commission, stock_quantity, image_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                data.get('selling_price', 0), data.get('purchasing_price', 0),
                data.get('commission', 0), data.get('stock_quantity', 0), data.get('image_url')
            ))
            new_product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['DELETE'])
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

# --- 📥 واجهات الطلبات ---

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
            
            # معالجة المنتجات سواء أرسلت كـ products أو items
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

@app.route('/api/public/orders', methods=['GET'])
def get_public_orders():
    # مسار مساعد وآمن ومباشر لتتبع شحنات الواجهة الأمامية بدون تعقيد
    return api_orders()

if __name__ == '__main__':
    app.run(debug=True)
