from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'sinai_store_401_secret_key_2026'

MY_WHATSAPP_NUMBER = "201065653401" 
ADMIN_PASSWORD = "010656534"

# الاتصال بقاعدة البيانات - ثابت ومستقر
def get_db_connection():
    db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url)
    return conn

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

# 🌟 قالب المتجر العام الجديد: مظهر احترافي، عصري، ومتجاوب بالكامل مع الهواتف
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 | Sinai Store</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #eab308;
            --primary-hover: #ca8a04;
            --bg-dark: #121212;
            --card-bg: #1e1e1e;
            --border-color: #333333;
            --text-main: #f3f4f6;
            --text-muted: #a3a3a3;
            --whatsapp-color: #22c55e;
        }
        
        body { 
            font-family: 'Cairo', sans-serif; 
            background-color: var(--bg-dark); 
            margin: 0; 
            padding: 0; 
            color: var(--text-main); 
        }

        /* هيدر عصري ومميز */
        nav { 
            background: rgba(30, 30, 30, 0.8);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border-color);
            padding: 15px 5%; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            position: sticky;
            top: 0;
            z-index: 100;
        }
        nav h1 { margin: 0; font-size: 24px; font-weight: 700; color: var(--primary); display: flex; align-items: center; gap: 10px; }
        
        .btn-portal {
            color: #111827; 
            font-weight: 600; 
            text-decoration: none; 
            background: #ffffff; 
            padding: 8px 16px; 
            border-radius: 8px; 
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .btn-portal:hover { background: var(--primary); }

        /* حاوية التصميم الرئيسي */
        .main-container { 
            max-width: 1300px; 
            margin: 30px auto; 
            padding: 0 20px; 
            display: grid; 
            grid-template-columns: 2.5fr 1fr; 
            gap: 30px; 
        }
        
        @media (max-width: 992px) { 
            .main-container { grid-template-columns: 1fr; } 
        }

        .section-title {
            color: var(--text-main);
            font-size: 20px;
            margin-top: 0;
            margin-bottom: 20px;
            border-right: 4px solid var(--primary);
            padding-right: 10px;
        }

        /* شبكة المنتجات الاحترافية */
        .products-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); 
            gap: 25px; 
        }
        
        .product-card { 
            background: var(--card-bg); 
            border: 1px solid var(--border-color); 
            border-radius: 14px; 
            overflow: hidden; 
            display: flex; 
            flex-direction: column; 
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .product-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.5);
            border-color: #444;
        }

        .product-img { width: 100%; height: 200px; object-fit: cover; background: #171717; }
        .no-img-placeholder { height: 200px; background: #171717; display: flex; align-items: center; justify-content: center; color: #444; font-size: 50px; }

        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: 600; margin: 0 0 10px 0; color: white; line-height: 1.4; }
        .price-badge-mini { color: var(--primary); font-weight: 700; font-size: 18px; margin-bottom: 12px; }
        
        .btn-whatsapp { 
            width: 100%; 
            padding: 10px; 
            background: var(--whatsapp-color); 
            color: white; 
            border: none; 
            border-radius: 8px; 
            font-size: 14px; 
            font-weight: 600; 
            cursor: pointer; 
            text-align: center; 
            text-decoration: none; 
            display: inline-block; 
            box-sizing: border-box;
            transition: background 0.3s ease;
        }
        .btn-whatsapp:hover { background: #16a34a; }

        /* كارت طلب الشراء الجانبي المستقر */
        .order-card { 
            background: var(--card-bg); 
            padding: 25px; 
            border-radius: 14px; 
            border: 1px solid var(--border-color); 
            border-top: 4px solid var(--primary); 
            height: fit-content; 
            position: sticky;
            top: 90px;
        }
        .order-card h2 { font-size: 20px; margin-top: 0; color: var(--primary); margin-bottom: 20px; }
        
        .form-group { margin-bottom: 18px; }
        .form-group label { display: block; font-size: 14px; margin-bottom: 8px; color: #d4d4d4; font-weight: 500; }
        .form-group input, .form-group select { 
            width: 100%; 
            padding: 12px; 
            background: #141414; 
            border: 1px solid var(--border-color); 
            border-radius: 8px; 
            box-sizing: border-box; 
            color: white; 
            font-size: 14px; 
            text-align: right; 
            font-family: 'Cairo', sans-serif;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: var(--primary);
        }
        
        .btn-yellow-submit { 
            width: 100%; 
            padding: 14px; 
            background: var(--primary); 
            color: #111827; 
            border: none; 
            border-radius: 8px; 
            font-size: 15px; 
            font-weight: 700; 
            cursor: pointer; 
            transition: background 0.3s ease;
            font-family: 'Cairo', sans-serif;
        }
        .btn-yellow-submit:hover { background: var(--primary-hover); }
    </style>
</head>
<body>

    <nav>
        <h1>🦅 سينا ستور 401</h1>
        <div>
            <a href="/marketers" class="btn-portal">👥 بوابة المسوقين</a>
        </div>
    </nav>

    <div class="main-container">
        <div>
            <h2 class="section-title">🛒 المنتجات المتوفرة في المخزن</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card">
                    {% if p.image_url %}
                        <img src="{{ p.image_url }}" class="product-img" alt="{{ p.name }}">
                    {% else %}
                        <div class="no-img-placeholder">📦</div>
                    {% endif %}
                    <div class="product-info">
                        <h3 class="product-title">{{ p.name }}</h3>
                        <div>
                            <div class="price-badge-mini">{{ p.selling_price }} ج.م</div>
                            <a href="https://api.whatsapp.com/send?phone={{ whatsapp }}&text=أريد+استفسار+عن+منتج:+{{ p.name }}" target="_blank" class="btn-whatsapp">💬 استفسار سريع</a>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: var(--text-muted); grid-column: 1/-1; text-align: center; padding: 40px;">لا توجد منتجات معروضة حالياً في المتجر.</p>
                {% endfor %}
            </div>
        </div>

        <div>
            <div class="order-card">
                <h2>🛍️ طلب شراء سريع</h2>
                <form action="/submit_order" method="POST">
                    <div class="form-group">
                        <label>اختر المنتج المطلوب:</label>
                        <select name="product_name" required>
                            {% for p in products %}
                            <option value="{{ p.name }}">{{ p.name }} — {{ p.selling_price }} ج.م</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>الكمية:</label>
                        <input type="number" name="quantity" value="1" min="1" required>
                    </div>
                    <div class="form-group">
                        <label>اسمك الكريم:</label>
                        <input type="text" name="customer_name" placeholder="الاسم ثلاثي" required>
                    </div>
                    <div class="form-group">
                        <label>رقم التليفون (للتواصل):</label>
                        <input type="text" name="customer_phone" placeholder="01xxxxxxxxx" required>
                    </div>
                    <div class="form-group">
                        <label>عنوان الشحن بالتفصيل:</label>
                        <input type="text" name="customer_address" placeholder="المحافظة - المدينة - الشارع" required>
                    </div>
                    <button type="submit" class="btn-yellow-submit">📦 تأكيد الطلب وإرسال عبر واتساب</button>
                </form>
            </div>
        </div>
    </div>

</body>
</html>
"""

# قالب بوابة المسوقين (تم ترقيته شكلياً فقط للحفاظ على استقرار المنطق)
HTML_MARKETERS = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>بوابة المسوقين | سينا ستور 401</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Cairo', sans-serif; background-color: #121212; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #f97316; color: white; padding: 15px 5%; display: flex; justify-content: space-between; align-items: center; }
        nav h1 { margin: 0; font-size: 22px; font-weight: 700; }
        .main-container { max-width: 1300px; margin: 30px auto; padding: 0 20px; display: grid; grid-template-columns: 2.5fr 1fr; gap: 30px; }
        @media (max-width: 992px) { .main-container { grid-template-columns: 1fr; } }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .product-card { background: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 15px; transition: transform 0.2s; }
        .product-card:hover { transform: scale(1.02); }
        .product-title { font-size: 16px; font-weight: 600; color: white; margin-bottom: 10px; }
        .price-badge { color: #f97316; font-weight: bold; margin-bottom: 5px; font-size: 15px; }
        .comm-badge { color: #22c55e; font-weight: bold; font-size: 15px; }
        .order-card { background: #1e1e1e; padding: 25px; border-radius: 12px; border: 1px solid #333; border-top: 4px solid #f97316; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input, .form-group select { width: 100%; padding: 11px; background: #141414; border: 1px solid #333; border-radius: 6px; color: white; text-align: right; font-family: 'Cairo'; }
        .btn-orange { width: 100%; padding: 12px; background: #f97316; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cairo'; font-size: 15px; }
    </style>
</head>
<body>
    <nav>
        <h1>🦅 بوابة المسوقين والعمولات</h1>
        <a href="/" style="color: white; text-decoration: none; font-weight: 600;">⬅️ العودة للمتجر الرئيسي</a>
    </nav>
    <div class="main-container">
        <div>
            <h2 style="border-right: 4px solid #f97316; padding-right: 10px;">📦 البضائع الحالية وعمولاتها</h2>
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
                        <label>المنتج العمول به:</label>
                        <select name="product_name" required>
                            {% for p in products %}
                            <option value="{{ p.name }}">{{ p.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <div class="form-group"><label>كود المسوق الخاص بك:</label><input type="text" placeholder="اكتب كودك هنا لتسجيل عمولتك" name="marketer_code" required></div>
                    <div class="form-group"><label>اسم الزبون:</label><input type="text" required></div>
                    <div class="form-group"><label>رقم هاتف الزبون:</label><input type="text" required></div>
                    <div class="form-group"><label>عنوان الزبون بالتفصيل:</label><input type="text" required></div>
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
