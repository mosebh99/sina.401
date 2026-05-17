import os
import sqlite3
from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

DB_FILE = "database.db"

# --- دالة الاتصال بقاعدة البيانات وإنشاء الجداول لو مش موجودة ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. جدول المنتجات (مع دعم حفظ الصور المضغوطة الطويلة جداً TEXT)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            selling_price REAL NOT NULL,
            stock_quantity INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')
    
    # 2. جدول طلبات الشحن (لحفظ طلبات الزباين والمسوقين)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            total_price REAL NOT NULL,
            marketer_id TEXT,
            products_json TEXT NOT NULL
        )
    ''')
    
    # إضافة منتجات تجريبية لو قاعدة البيانات لسه جديدة تماماً وفاضية
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("زيت زيتون سيناوي بكر ممتاز", "زيوت طبيعية", 250.0, 15, "logo.png", "زيت زيتون طبيعي 100% من معاصر سيناء بجودة عالية وفائقة."),
            ("عشب المرمية السيناوية الجبلية", "أعشاب طبيعية", 85.0, 30, "logo.png", "مرمية برية طبيعية مجففة ومقطوفة بعناية من جبال سيناء الطبيعية.")
        ]
        cursor.executemany('''
            INSERT INTO products (name, category, selling_price, stock_quantity, image_url, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
        
    conn.commit()
    conn.close()

# تشغيل قاعدة البيانات فوراً عند إقلاع السيرفر
init_db()

# --- مسارات توجيه الصفحات الفردية ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/cashier.html')
def cashier(): 
    return render_template('cashier.html')


# =======================================================
# 🛒 أولاً: لوحة تحكم المنتجات (جلب / إضافة / تعديل / مسح)
# =======================================================

# 1. جلب كل المنتجات من قاعدة البيانات الثابتة
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    products_list = []
    for row in rows:
        products_list.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "selling_price": row["selling_price"],
            "stock_quantity": row["stock_quantity"],
            "image_url": row["image_url"],
            "description": row["description"]
        })
    return jsonify(products_list), 200

# 2. إضافة منتج جديد وحفظه في ملف قاعدة البيانات
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, category, selling_price, stock_quantity, image_url, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['name'], data.get('category', 'عام'), float(data['selling_price']), int(data['stock_quantity']), data['image_url'], data['description']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Product added successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# 3. تعديل وتحديث بيانات منتج موجود بالمعرف بتاعه (ID)
@app.route('/api/products/<int:p_id>', methods=['PUT'])
def update_product(p_id):
    data = request.get_json()
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE products 
            SET name=?, selling_price=?, stock_quantity=?, image_url=?, description=?
            WHERE id=?
        ''', (data['name'], float(data['selling_price']), int(data['stock_quantity']), data['image_url'], data['description'], p_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Product updated successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# 4. مسح منتج نهائياً من المتجر
@app.route('/api/products/<int:p_id>', methods=['DELETE'])
def delete_product(p_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (p_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Product deleted successfully"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# =======================================================
# 📦 ثانياً: لوحة تحكم طلبات الشحن (تأكيد الطلبات / عرضها)
# =======================================================

# 1. استقبال طلب شراء جديد من سلة المشتريات وتخزينه فوراً للمدير
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    import json
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # تحويل مصفوفة المنتجات لنص جيسون متوافق مع قواعد البيانات
        products_json_str = json.dumps(data['products'], ensure_ascii=False)
        
        cursor.execute('''
            INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_id, products_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['customer_name'], data['customer_phone'], data['customer_address'], float(data['total']), data.get('marketer_id'), products_json_str))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Order placed successfully"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# 2. جلب كل طلبات الشحن الحالية لتعرض في صفحة المدير
@app.route('/api/orders', methods=['GET'])
def get_orders():
    import json
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    orders_list = []
    for row in rows:
        orders_list.append({
            "id": row["id"],
            "customer_name": row["customer_name"],
            "customer_phone": row["customer_phone"],
            "customer_address": row["customer_address"],
            "total": row["total_price"],
            "marketer_id": row["marketer_id"],
            "products": json.loads(row["products_json"]) # فك النص ليعود كـ مصفوفة برمجية
        })
    return jsonify(orders_list), 200


# تشغيل الخادم السحابي
application = app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
