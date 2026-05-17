from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'sinai_store_401_secret_key_2026'

MY_WHATSAPP_NUMBER = "201065653401" 
ADMIN_PASSWORD = "010656534"

# الاتصال بقاعدة البيانات
def get_db_connection():
    db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url)
    return conn

# إنشاء الجدول الأساسي للمنتجات في حالة عدم وجوده
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            purchase_price NUMERIC DEFAULT 0,
            selling_price NUMERIC DEFAULT 0,
            commission NUMERIC DEFAULT 0,
            stock_quantity INTEGER DEFAULT 1,
            image_url TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print("Database init error:", e)

# القالب القديم والمستقر للمتجر العام
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - المتجر الرئيسي</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .main-container { max-width: 1200px; margin: 25px auto; padding: 0 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; }
        .product-img { width: 100%; height: 180px; object-fit: cover; background: #171717; }
        .product-info { padding: 12px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 15px; font-weight: bold; margin: 0 0 8px 0; color: white; }
        .price-badge-mini { color: #eab308; font-weight: bold; font-size: 15px; margin-bottom: 6px; }
        .btn-whatsapp { width: 100%; padding: 8px; background: #22c55e; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer; text-align: center; text-decoration: none; display: block; box-sizing: border-box; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #eab308; height: fit-content; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-yellow-submit { width: 100%; padding: 12px; background: #eab308; color: #111827; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 180px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
    </style>
</head>
<body>

    <nav>
        <h1>🦅 سينا ستور 401</h1>
        <div style="display: flex; gap: 10px;">
            <a href="/marketers" style="color: #111827; font-weight: bold; text-decoration: none; background: #ffffff; padding: 5px 10px; border-radius: 4px; font-size: 13px;">👥 بوابة المسوقين</a>
        </div>
    </nav>

    <div class="main-container">
        <div>
            <h2 style="color: #eab308; margin-top: 0;">🛒 المنتجات المعروضة</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card">
                    {% if p.image_url %}<img src="{{ p.image_url }}" class="product-img">{% else %}<div class="no-img-placeholder">📱</div>{% endif %}
                    <div class="product-info">
                        <h3 class="product-title">{{ p.name }}</h3>
                        <div>
                            <div class="price-badge-mini">السعر: {{ p.selling_price }} ج.م</div>
                            <a href="https://api.whatsapp.com/send?phone={{ whatsapp }}&text=أريد+طلب+منتج:+{{ p.name }}" target="_blank" class="btn-whatsapp">💬 اطلب عبر واتساب</a>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: #a3a3a3;">لا توجد منتجات متوفرة حالياً.</p>
                {% endfor %}
            </div>
        </div>

        <div>
            <div class="order-card">
                <h2>🛍️ نموذج الشراء السريع</h2>
                <form action="/submit_order" method="POST">
                    <div class="form-group">
                        <label>اختر المنتج:</label>
                        <select name="product_name" required>
                            {% for p in products %}
                            <option value="{{ p.name }}">{{ p.name }} - {{ p.selling_price }} ج.م</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <div class="form-group"><label>الاسم الكامل:</label><input type="text" name="customer_name" required></div>
                    <div class="form-group"><label>رقم التليفون:</label><input type="text" name="customer_phone" required></div>
                    <div class="form-group"><label>العنوان بالتفصيل:</label><input type="text" name="customer_address" required></div>
                    <button type="submit" class="btn-yellow-submit">📦 إرسال الطلب للواتساب</button>
                </form>
            </div>
        </div>
    </div>

</body>
</html>
"""

# القالب القديم لبوابة المسوقين والعمولات
HTML_MARKETERS = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوابة المسوقين - سينا ستور 401</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #f97316; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        nav h1 { margin: 0; font-size: 20px; font-weight: bold; }
        .main-container { max-width: 1200px; margin: 20px auto; padding: 0 15px; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; padding: 10px; }
        .product-title { font-size: 16px; font-weight: bold; color: white; margin: 5px 0; }
        .price-badge { color: #f97316; font-weight: bold; margin-bottom: 5px; }
        .comm-badge { color: #22c55e; font-weight: bold; font-size: 14px; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border-top: 5px solid #f97316; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; color: white; text-align: right; }
        .btn-orange { width: 100%; padding: 12px; background: #f97316; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <nav>
        <h1>🦅 بوابة المسوقين والعمولات</h1>
        <a href="/" style="color: white; text-decoration: none;">⬅️ المتجر العام</a>
    </nav>
    <div class="main-container">
        <div>
            <h2>📦 البضائع المتاحة وعمولاتها</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card">
                    <div class="product-title">{{ p.name }}</div>
                    <div class="price-badge">سعر الزبون: {{ p.selling_price }} ج.م</div>
                    <div class="comm-badge">عمولتك: {{ p.commission }} ج.م</div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div>
            <div class="order-card">
                <h2>📣 إرسال طلب مسوق جديد</h2>
                <form action="/submit_marketer_order" method="POST">
                    <div class="form-group">
                        <label>المنتج:</label>
                        <select name="product_name" required>
                            {% for p in products %}
                            <option value="{{ p.name }}">{{ p.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <div class="form-group"><label>كود المسوق:</label><input type="text" name="marketer_code" required></div>
                    <div class="form-group"><label>اسم الزبون:</label><input type="text" name="customer_name" required></div>
                    <div class="form-group"><label>رقم هاتف الزبون:</label><input type="text" name="customer_phone" required></div>
                    <div class="form-group"><label>عنوان الزبون:</label><input type="text" name="customer_address" required></div>
                    <button type="submit" class="btn-orange">📣 إرسال الطلب عبر واتساب</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id DESC;")
        db_products = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        db_products = []
        print("Error:", e)
    return render_template_string(HTML_INDEX, products=db_products, whatsapp=MY_WHATSAPP_NUMBER)

@app.route('/marketers')
def marketers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM products ORDER BY id DESC;")
        db_products = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        db_products = []
    return render_template_string(HTML_MARKETERS, products=db_products)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    p_name = request.form.get('product_name')
    qty = request.form.get('quantity')
    c_name = request.form.get('customer_name')
    c_phone = request.form.get('customer_phone')
    c_address = request.form.get('customer_address')
    
    text = f"🛒 *طلب شراء جديد*\\n\\n📦 *المنتج:* {p_name}\\n🔢 *الكمية:* {qty}\\n👤 *العميل:* {c_name}\\n📞 *الهاتف:* {c_phone}\\n📍 *العنوان:* {c_address}"
    return redirect(f"https://api.whatsapp.com/send?phone={MY_WHATSAPP_NUMBER}&text={text}")

@app.route('/submit_marketer_order', methods=['POST'])
def submit_marketer_order():
    p_name = request.form.get('product_name')
    qty = request.form.get('quantity')
    m_code = request.form.get('marketer_code')
    c_name = request.form.get('customer_name')
    c_phone = request.form.get('customer_phone')
    c_address = request.form.get('customer_address')
    
    text = f"📣 *طلب مسوق بالعمولة*\\n\\n👥 *المسوق:* {m_code}\\n📦 *المنتج:* {p_name}\\n🔢 *الكمية:* {qty}\\n👤 *الزبون:* {c_name}\\n📞 *الرقم:* {c_phone}\\n📍 *العنوان:* {c_address}"
    return redirect(f"https://api.whatsapp.com/send?phone={MY_WHATSAPP_NUMBER}&text={text}")

if __name__ == '__main__':
    app.run(debug=True)
