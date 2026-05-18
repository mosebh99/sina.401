import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app = app  # السطر السحري الإجباري لمنصة Vercel لمنع الـ Failed

# رابط الاتصال المباشر والمؤمن بقاعدة بيانات Supabase
DATABASE_URL = "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    """إنشاء اتصال مؤمن بالسيرفر السحابي لضمان ثبات الاتصال"""
    conn = psycopg2.connect(DATABASE_URL, sslmode='allow', cursor_factory=RealDictCursor)
    return conn

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

@app.route('/product/<int:product_id>')
def product_detail_page(product_id):
    return render_template('product_detail.html')

# ==========================================
# 📊 مسارات البيانات الخلفية (API Routes)
# ==========================================

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT * FROM products ORDER BY id DESC;")
            products = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(products)
        elif request.method == 'POST':
            data = request.json
            cur.execute("""
                INSERT INTO products (name, category, cost_price, selling_price, stock_qty, image_url, description, extra_images)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('cost_price', 0),
                data.get('selling_price', 0), data.get('stock_qty', 0),
                data.get('image_url'), data.get('description'), json.dumps(data.get('extra_images', []))
            ))
            new_product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def api_single_product(pid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        if request.method == 'GET':
            cur.execute("SELECT * FROM products WHERE id = %s;", (pid,))
            p = cur.fetchone()
            cur.close()
            conn.close()
            if p: return jsonify(p)
            return jsonify({"error": "المنتج غير موجود"}), 404
        elif request.method == 'PUT':
            data = request.json
            cur.execute("""
                UPDATE products SET name=%s, category=%s, cost_price=%s, selling_price=%s, 
                stock_qty=%s, image_url=%s, description=%s, extra_images=%s WHERE id=%s RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('cost_price'), data.get('selling_price'),
                data.get('stock_qty'), data.get('image_url'), data.get('description'), json.dumps(data.get('extra_images', [])), pid
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
            data = request.json
            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, items, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('customer_name'), data.get('customer_phone'), data.get('customer_address'),
                data.get('total_price', 0), data.get('marketer_id'), json.dumps(data.get('items', [])),
                data.get('status', 'قيد المراجعة')
            ))
            new_order = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_order), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
