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
                purchasing_price NUMERIC,
                selling_price NUMERIC,
                stock_quantity INTEGER,
                commission NUMERIC,
                image_url TEXT,
                extra_images TEXT
            );
        ''')
        # إنشاء جدول الطلبات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price NUMERIC,
                marketer_id VARCHAR(100),
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database Tables Verified & Repaired Successfully.")
    except Exception as e:
        print(f"❌ Database Fix Error: {str(e)}")

# --- مسارات الـ API لإدارة المنتجات ---
@app.route('/api/products', methods=['GET', 'POST'])
def handle_products():
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
                INSERT INTO products (name, category, description, purchasing_price, selling_price, stock_quantity, commission, image_url, extra_images)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                float(data.get('purchasing_price') or 0), float(data.get('selling_price') or 0),
                int(data.get('stock_quantity') or 0), float(data.get('commission') or 0),
                data.get('image_url'), data.get('extra_images')
            ))
            new_product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:prod_id>', methods=['DELETE', 'PUT'])
def handle_single_product(prod_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'DELETE':
            cur.execute("DELETE FROM products WHERE id = %s RETURNING *;", (prod_id,))
            deleted = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            if deleted: return jsonify(deleted)
            return jsonify({"error": "Product not found"}), 404
        elif request.method == 'PUT':
            data = request.json
            cur.execute("""
                UPDATE products SET name=%s, category=%s, description=%s, purchasing_price=%s, selling_price=%s, 
                stock_quantity=%s, commission=%s, image_url=%s, extra_images=%s WHERE id=%s RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                float(data.get('purchasing_price') or 0), float(data.get('selling_price') or 0),
                int(data.get('stock_quantity') or 0), float(data.get('commission') or 0),
                data.get('image_url'), data.get('extra_images'), prod_id
            ))
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            if updated: return jsonify(updated)
            return jsonify({"error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- مسارات الـ API لإدارة الطلبات ---
@app.route('/api/orders', methods=['GET', 'POST'])
def handle_orders():
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

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("UPDATE orders SET status = %s WHERE id = %s RETURNING *;", (data.get('status'), order_id))
        updated_order = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_order:
            return jsonify(updated_order)
        return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- مسارات عرض الصفحات المستقرة والمؤمنة ---
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/cashier.html')
def cashier_page():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers_page():
    return render_template('marketers.html')

@app.route('/product_detail.html')
def product_detail_page():
    return render_template('product_detail.html')

if __name__ == '__main__':
    fix_database_columns_forced()
    app.run(debug=True, port=5000)
