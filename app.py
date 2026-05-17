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

# تهيئة الجداول في قاعدة البيانات
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

# ---------------------------------------------------------
# 1. قالب المتجر العام الجديد للزبائن
# ---------------------------------------------------------
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 | Sinai Store</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #eab308; --bg-dark: #121212; --card-bg: #1e1e1e; --border-color: #333; --text-main: #f3f4f6; }
        body { font-family: 'Cairo', sans-serif; background-color: var(--bg-dark); margin: 0; padding: 0; color: var(--text-main); }
        nav { background: rgba(30, 30, 30, 0.9); border-bottom: 1px solid var(--border-color); padding: 15px 5%; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        nav h1 { margin: 0; font-size: 24px; color: var(--primary); font-weight: 700; }
        .btn-portal { color: #111827; font-weight: 600; text-decoration: none; background: #ffffff; padding: 8px 16px; border-radius: 8px; font-size: 14px; transition: 0.3s; }
        .btn-portal:hover { background: var(--primary); }
        .main-container { max-width: 1300px; margin: 30px auto; padding: 0 20px; display: grid; grid-template-columns: 2.5fr 1fr; gap: 30px; }
        @media (max-width: 992px) { .main-container { grid-template-columns: 1fr; } }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 20px; }
        .product-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; transition: 0.3s; }
        .product-card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
        .product-img { width: 100%; height: 190px; object-fit: cover; background: #171717; }
        .no-img-placeholder { height: 190px; background: #171717; display: flex; align-items: center; justify-content: center; font-size: 40px; }
        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: 600; margin: 0 0 10px 0; color: white; }
        .price-badge-mini { color: var(--primary); font-weight: 700; font-size: 17px; margin-bottom: 10px; }
        .btn-whatsapp { width: 100%; padding: 10px; background: #22c55e; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; text-decoration: none; display: block; text-align: center; box-sizing: border-box; }
        .order-card { background: var(--card-bg); padding: 25px; border-radius: 12px; border: 1px solid var(--border-color); border-top: 4px solid var(--primary); height: fit-content; position: sticky; top: 90px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input, .form-group select { width: 100%; padding: 11px; background: #141414; border: 1px solid var(--border-color); border-radius: 7px; color: white; text-align: right; font-family: 'Cairo'; box-sizing: border-box; }
        .btn-yellow-submit { width: 100%; padding: 13px; background: var(--primary); color: #111827; border: none; border-radius: 7px; font-size: 15px; font-weight: 700; cursor: pointer; font-family: 'Cairo'; }
    </style>
</head>
<body>
    <nav>
        <h1>🦅 سينا ستور 401</h1>
        <div style="display: flex; gap: 10px;">
            <a href="/marketers" class="btn-portal">👥 بوابة المسوقين</a>
            <a href="/admin" class="btn-portal" style="background: #374151; color: white;">⚙️ لوحة الإدارة</a>
        </div>
    </nav>
    <div class="main-container">
        <div>
            <h2 style="border-right: 4px solid var(--primary); padding-right:10px;">🛒 المعروضات الحالية</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card">
                    {% if p.image_url %}<img src="{{ p.image_url }}" class="product-img">{% else %}<div class="no-img-placeholder">📦</div>{% endif %}
                    <div class="product-info">
                        <h3 class="product-title">{{ p.name }}</h3>
                        <div>
                            <div class="price-badge-mini">السعر: {{ p.selling_price }} ج.م</div>
                            <a href="https://api.whatsapp.com/send?phone={{ whatsapp }}&text=أريد+طلب+منتج:+{{ p.name }}" target="_blank" class="btn-whatsapp">💬 طلب عبر واتساب</a>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: #a3a3a3; text-align: center; grid-column: 1/-1;">لا توجد بضائع معروضة حالياً.</p>
                {% endfor %}
            </div>
        </div>
        <div>
            <div class="order-card">
                <h2>🛍️ نموذج الشراء السريع</h2>
                <form action="/submit_order" method="POST">
                    <div class="form-group">
                        <label>المنتج المطلوب:</label>
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

# ---------------------------------------------------------
# 2. قالب بوابة المسوقين والعمولات
# ---------------------------------------------------------
HTML_MARKETERS = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>بوابة المسوقين | سينا ستور 401</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #121212; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #f97316; color: white; padding: 15px 5%; display: flex; justify-content: space-between; align-items: center; }
        .main-container { max-width: 1300px; margin: 30px auto; padding: 0 20px; display: grid; grid-template-columns: 2.5fr 1fr; gap: 30px; }
        @media (max-width: 992px) { .main-container { grid-template-columns: 1fr; } }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .product-card { background: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 15px; }
        .product-title { font-size: 16px; font-weight: 600; color: white; margin-bottom: 8px; }
        .price-badge { color: #f97316; font-weight: bold; }
        .comm-badge { color: #22c55e; font-weight: bold; }
        .order-card { background: #1e1e1e; padding: 25px; border-radius: 12px; border-top: 4px solid #f97316; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input, .form-group select { width: 100%; padding: 11px; background: #141414; border: 1px solid #333; border-radius: 6px; color: white; text-align: right; font-family: 'Cairo'; box-sizing: border-box; }
        .btn-orange { width: 100%; padding: 12px; background: #f97316; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo'; }
    </style>
</head>
<body>
    <nav>
        <h2>🦅 بوابة المسوقين والعمولات</h2>
        <a href="/" style="color: white; text-decoration: none; font-weight: 600;">⬅️ المتجر الرئيسي</a>
    </nav>
    <div class="main-container">
        <div>
            <h2 style="border-right: 4px solid #f97316; padding-right: 10px;">📦 البضائع الحالية والعمولات بالجنيه</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card">
                    <div class="product-title">{{ p.name }}</div>
                    <div class="price-badge">سعر الزبون: {{ p.selling_price }} ج.م</div>
                    <div class="comm-badge">عمولتك الثابتة: {{ p.commission }} ج.م</div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div>
            <div class="order-card">
                <h2>📣 تسجيل طلب مسوق</h2>
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
                    <div class="form-group"><label>كود المسوق الخاص بك:</label><input type="text" name="marketer_code" placeholder="مثال: M10" required></div>
                    <div class="form-group"><label>اسم الزبون:</label><input type="text" name="customer_name" required></div>
                    <div class="form-group"><label>رقم هاتف الزبون:</label><input type="text" name="customer_phone" required></div>
                    <div class="form-group"><label>عنوان الزبون:</label><input type="text" name="customer_address" required></div>
                    <button type="submit" class="btn-orange">📣 إرسال الطلب لسيستم الواتساب</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ---------------------------------------------------------
# 3. قالب لوحة التحكم المتقدمة (المدير والكاشير مع الحسابات)
# ---------------------------------------------------------
HTML_ADMIN = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة الإدارة المتقدمة | سينا ستور</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #0f172a; margin: 0; padding: 0; color: #f8fafc; }
        nav { background: #1e293b; padding: 15px 5%; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; }
        .container { max-width: 1350px; margin: 30px auto; padding: 0 20px; }
        
        /* كروت الإحصائيات المالية المتقدمة */
        .stats-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }
        .stat-card h3 { margin: 0 0 10px 0; font-size: 15px; color: #94a3b8; font-weight: 600; }
        .stat-card .value { font-size: 26px; font-weight: 700; color: white; }
        .stat-card.total-purchase { border-top: 4px solid #3b82f6; }
        .stat-card.total-sales { border-top: 4px solid #eab308; }
        .stat-card.total-commissions { border-top: 4px solid #f97316; }
        .stat-card.expected-profit { border-top: 4px solid #22c55e; }
        .stat-card.expected-profit .value { color: #22c55e; }

        .grid { display: grid; grid-template-columns: 1fr 2.5fr; gap: 30px; }
        @media (max-width: 992px) { .grid { grid-template-columns: 1fr; } }
        
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); height: fit-content; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-size: 14px; color: #cbd5e1; }
        .form-group input { width: 100%; padding: 11px; background: #0f172a; border: 1px solid #475569; border-radius: 6px; color: white; text-align: right; font-family: 'Cairo'; box-sizing: border-box; }
        .btn-submit { width: 100%; padding: 12px; background: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo'; font-size: 15px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; background: #1e293b; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 15px; text-align: right; border-bottom: 1px solid #334155; }
        th { background: #334155; color: #3b82f6; font-weight: 600; }
        .btn-delete { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 13px; font-family: 'Cairo'; }
        .alert { background: #22c55e; padding: 12px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
    </style>
</head>
<body>
    <nav>
        <h2>⚙️ لوحة تحكم وإدارة الخزينة والمخزن الحقيقي</h2>
        <div>
            <a href="/" style="color: #cbd5e1; text-decoration: none; margin-left: 15px; font-weight: 600;">🏪 المتجر العام</a>
            <a href="/admin/logout" style="color: #ef4444; text-decoration: none; font-weight: bold;">🚪 تسجيل الخروج</a>
        </div>
    </nav>
    <div class="container">
        
        <div class="stats-container">
            <div class="stat-card total-purchase">
                <h3>💰 إجمالي رأس المال بالمخزن (تكلفة الشراء)</h3>
                <div class="value">{{ stats.total_purchase }} ج.م</div>
            </div>
            <div class="stat-card total-sales">
                <h3>💵 القيمة البيعية الإجمالية للبضاعة</h3>
                <div class="value">{{ stats.total_sales }} ج.م</div>
            </div>
            <div class="stat-card total-commissions">
                <h3>👥 إجمالي عمولات المسوقين المحجوزة</h3>
                <div class="value">{{ stats.total_commissions }} ج.م</div>
            </div>
            <div class="stat-card expected-profit">
                <h3>📈 صافي الأرباح المحتملة (بعد العمولات)</h3>
                <div class="value">{{ stats.expected_profit }} ج.م</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3 style="color: #3b82f6; margin-top:0; border-bottom: 1px solid #334155; padding-bottom: 10px;">➕ إدارة المنتجات</h3>
                <form action="/admin/add" method="POST">
                    <div class="form-group"><label>اسم السلعة/المنتج:</label><input type="text" name="name" required placeholder="مثال: عباية سيناوي"></div>
                    <div class="form-group"><label>سعر الشراء الأساسي (ج.م):</label><input type="number" step="0.01" name="purchase_price" value="0"></div>
                    <div class="form-group"><label>سعر البيع النهائي للزبون (ج.م):</label><input type="number" step="0.01" name="selling_price" value="0" required></div>
                    <div class="form-group
