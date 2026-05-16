from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'sinai_store_401_secret_key_2026'

MY_WHATSAPP_NUMBER = "201065653401" 
ADMIN_PASSWORD = "010656534"

# الاتصال بقاعدة البيانات باستخدام الرابط التلقائي من فيرسيل
def get_db_connection():
    # فيرسيل بيوفر الرابط في متغير POSTGRES_URL أو DATABASE_URL تلقائياً
    db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        # تعديل بسيط لضمان توافق المكتبة مع الروابط الحديثة
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    conn = psycopg2.connect(db_url)
    return conn

# إنشاء جدول المنتجات تلقائياً لو مش موجود أول ما الموقع يفتح
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

# --- 🔑 شاشة تسجيل الدخول للمدير ---
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - تسجيل دخول الإدارة</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background: #262626; padding: 30px; border-radius: 12px; border: 1px solid #404040; border-top: 5px solid #eab308; width: 100%; max-width: 360px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); box-sizing: border-box; }
        h2 { margin-top: 0; text-align: center; color: #eab308; font-size: 18px; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 8px; color: #d4d4d4; }
        .form-group input { width: 100%; padding: 12px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; text-align: center; font-size: 16px; letter-spacing: 2px; }
        button { width: 100%; padding: 12px; background: #eab308; color: #111827; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .error-msg { color: #ef4444; font-size: 13px; text-align: center; margin-bottom: 15px; font-weight: bold; }
        .back-btn { display: block; text-align: center; margin-top: 15px; color: #a3a3a3; text-decoration: none; font-size: 12px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🦅 تسجيل دخول الإدارة والكاشير</h2>
        {% if error %}
            <div class="error-msg">{{ error }}</div>
        {% endif %}
        <form action="/cashier_login" method="POST">
            <div class="form-group">
                <label>أدخل رمز الأمان السري:</label>
                <input type="password" name="password" required placeholder="•••••" autofocus>
            </div>
            <button type="submit">🔓 دخول إلى اللوحة</button>
        </form>
        <a href="/" class="back-btn">⬅️ العودة للمتجر العام</a>
    </div>
</body>
</html>
"""

# --- 1️⃣ صفحة المتجر الرئيسي (مجهزة بالكامل لمحركات بحث جوجل SEO) ---
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - المتجر الإلكتروني الرسمي</title>
    <meta name="description" content="متجر سينا ستور 401 لبيع أفضل المنتجات والملابس أونلاين بأفضل الأسعار. تسوق الآن واستمتع بشحن سريع ودعم فوري عبر الواتساب.">
    <meta name="keywords" content="سينا ستور, سينا 401, متجر سينا, تسوق أونلاين مصر, ملابس أونلاين, شراء منتجات">
    <meta name="robots" content="index, follow">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 20px; font-weight: bold; }
        .nav-links { display: flex; gap: 8px; }
        .nav-btn { background: #111827; color: white; padding: 8px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #374151; }
        .main-container { max-width: 1200px; margin: 20px auto; padding: 0 15px; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .search-box { width: 100%; padding: 12px; background: #262626; border: 1px solid #404040; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 20px; box-sizing: border-box; text-align: right; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
        .product-img { width: 100%; height: 180px; object-fit: cover; background: #171717; }
        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: bold; margin: 0 0 5px 0; color: white; }
        .product-desc { font-size: 13px; color: #a3a3a3; margin: 0 0 12px 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .price-badge { background: #171717; border: 1px solid #eab308; color: #eab308; padding: 8px 10px; border-radius: 5px; font-weight: bold; font-size: 15px; text-align: center; margin-bottom: 10px; }
        .stock-count { font-size: 12px; color: #a3a3a3; text-align: center; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #eab308; height: fit-content; position: sticky; top: 20px; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; color: #eab308; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-yellow-submit { width: 100%; padding: 12px; background: #eab308; color: #111827; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 180px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
    </style>
</head>
<body>
    <nav>
        <h1>🦅 سينا ستور 401 - المتجر الرئيسي</h1>
        <div class="nav-links">
            <a href="/marketers" class="nav-btn">👥 بوابة المسوقين</a>
            <a href="/cashier" class="nav-btn" style="background:#404040;">🖥️ الكاشير والإدارة</a>
        </div>
    </nav>
    <div class="main-container">
        <div>
            <input type="text" id="search-input" class="search-box" placeholder="🔍 ابحث عن منتج داخل المتجر..." oninput="filterProducts()">
            <h2>🛒 المنتجات المتاحة حالياً للطلب</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card item-card" data-name="{{ p.name.lower() }}" style="{% if p.stock_quantity <= 0 %}opacity:0.4;{% endif %}">
                    {% if p.image_url %}<img src="{{ p.image_url }}" class="product-img" alt="{{ p.name }}">{% else %}<div class="no-img-placeholder">📱</div>{% endif %}
                    <div class="product-info">
                        <div>
                            <h3 class="product-title">{{ p.name }}</h3>
                            <p class="product-desc">{% if p.description %}{{ p.description }}{% else %}لا يوجد وصف متاح حالياً لهذا المنتج.{% endif %}</p>
                        </div>
                        <div>
                            <div class="price-badge">السعر: {{ p.selling_price }} ج.م</div>
                            <div class="stock-count">{% if p.stock_quantity <= 0 %}❌ نفذت الكمية مؤقتاً{% else %}متوفر في المخزن: {{ p.stock_quantity }} قطعة{% endif %}</div>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: #a3a3a3; grid-column: 1/-1; text-align: center; padding: 20px;">لا توجد منتجات معروضة حالياً في المتجر.</p>
                {% endfor %}
            </div>
        </div>
        <div>
            <div class="order-card">
                <h2>🛍️ نموذج الشراء الفوري أونلاين</h2>
                <form onsubmit="submitCustomerOrder(event)">
                    <div class="form-group">
                        <label>اختر المنتج الذي تريد شراءه:</label>
                        <select id="cust-product-select" required>
                            <option value="">-- اضغط واختر المنتج --</option>
                            {% for p in products %}{% if p.stock_quantity > 0 %}
                            <option value="{{ p.name }}" data-price="{{ p.selling_price }}">{{ p.name }}</option>
                            {% endif %}{% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية المطلوبة:</label><input type="number" id="cust-qty" value="1" min="1" required></div>
                    <div class="form-group"><label>اسمك بالكامل:</label><input type="text" id="cust-name" required placeholder="الاسم ثلاثي"></div>
                    <div class="form-group"><label>رقم هاتف للتواصل:</label><input type="text" id="cust-phone" required></div>
                    <div class="form-group"><label>عنوان التوصيل بالتفصيل:</label><input type="text" id="cust-address" required></div>
                    <button type="submit" class="btn-yellow-submit">📦 إرسال طلب الشراء عبر الواتساب</button>
                </form>
            </div>
        </div>
    </div>
    <script>
        function filterProducts() {
            let q = document.getElementById('search-input').value.toLowerCase().trim();
            document.querySelectorAll('.item-card').forEach(card => {
                card.style.display = card.getAttribute('data-name').includes(q) ? '' : 'none';
            });
        }
        function submitCustomerOrder(e) {
            e.preventDefault();
            let sel = document.getElementById('cust-product-select');
            if(!sel.value) return alert("من فضلك اختر منتج أولاً");
            let prod = sel.value;
            let price = parseFloat(sel.options[sel.selectedIndex].getAttribute('data-price'));
            let qty = parseInt(document.getElementById('cust-qty').value);
            let name = document.getElementById('cust-name').value;
            let phone = document.getElementById('cust-phone').value;
            let addr = document.getElementById('cust-address').value;
            let msg = `🛒 *طلب شراء جديد من المتجر - سينا ستور 401*\\n\\n📦 *المنتج:* ${prod}\\n🔢 *الكمية:* ${qty} قطعة\\n💰 *الحساب:* ${price*qty} ج.م\\n-----------------------------------------\\n👤 *العميل:* ${name}\\n📞 *الهاتف:* ${phone}\\n📍 *العنوان:* ${addr}`;
            window.location.href = `https://api.whatsapp.com/send?phone={{ whatsapp }}&text=${encodeURIComponent(msg)}`;
        }
    </script>
</body>
</html>
"""

# --- 2️⃣ صفحة بوابة المسوقين والعمولات ---
HTML_MARKETERS = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - بوابة المسوقين والعمولات</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #f97316; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 20px; font-weight: bold; }
        .nav-links { display: flex; gap: 8px; }
        .nav-btn { background: #111827; color: white; padding: 8px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #374151; }
        .main-container { max-width: 1200px; margin: 20px auto; padding: 0 15px; display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .search-box { width: 100%; padding: 12px; background: #262626; border: 1px solid #404040; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 20px; box-sizing: border-box; text-align: right; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
        .product-img { width: 100%; height: 180px; object-fit: cover; background: #171717; }
        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: bold; margin: 0 0 5px 0; color: white; }
        .product-desc { font-size: 13px; color: #a3a3a3; margin: 0 0 12px 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .price-badge { background: #171717; border: 1px solid #f97316; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 8px; }
        .comm-badge { background: #ffedd5; color: #c2410c; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 10px; border: 1px solid #f97316; }
        .stock-count { font-size: 12px; color: #a3a3a3; text-align: center; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #f97316; height: fit-content; position: sticky; top: 20px; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; color: #f97316; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-orange { width: 100%; padding: 12px; background: #f97316; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 180px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
    </style>
</head>
<body>
    <nav>
        <h1>🦅 سينا ستور 401 - لوحة العمولات والمسوقين</h1>
        <div class="nav-links"><a href="/" class="nav-btn">⬅️ المتجر العام</a></div>
    </nav>
    <div class="main-container">
        <div>
            <input type="text" id="m-search" class="search-box" placeholder="🔍 ابحث عن منتج لمعرفة عمولته..." oninput="filterMProducts()">
            <h2>📦 قائمة بضائع وعمولات الأونلاين الحالية</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card m-card" data-name="{{ p.name.lower() }}" style="{% if p.stock_quantity <= 0 %}opacity:0.4;{% endif %}">
                    {% if p.image_url %}<img src="{{ p.image_url }}" class="product-img" alt="{{ p.name }}">{% else %}<div class="no-img-placeholder">📱</div>{% endif %}
                    <div class="product-info">
                        <div>
                            <h3 class="product-title">{{ p.name }}</h3>
                            <p class="product-desc">{% if p.description %}{{ p.description }}{% else %}لا يوجد وصف متاح لهذا المنتج.{% endif %}</p>
                        </div>
                        <div>
                            <div class="price-badge">💰 سعر الزبون: {{ p.selling_price }} ج.م</div>
                            <div class="comm-badge">🎁 عمولتك الصافية: {{ p.commission }} ج.م</div>
                            <div class="stock-count">{% if p.stock_quantity <= 0 %}❌ عجز مخزون{% else %}المتاح جردياً: {{ p.stock_quantity }} قطعة{% endif %}</div>
                        </div>
                    </div>
                </div>
                {% else %}
                <p style="color: #a3a3a3; grid-column: 1/-1; text-align: center; padding: 20px;">لا توجد بضائع معروضة حالياً.</p>
                {% endfor %}
            </div>
        </div>
        <div>
            <div class="order-card">
                <h2>📣 إرسال طلب أونلاين جديد بالعمولة</h2>
                <form onsubmit="submitMarketerOrder(event)">
                    <div class="form-group">
                        <label>اختر المنتج المطلوب:</label>
                        <select id="marketer-product-select" required>
                            <option value="">-- اضغط واختر المنتج --</option>
                            {% for p in products %}{% if p.stock_quantity > 0 %}
                            <option value="{{ p.name }}" data-comm="{{ p.commission }}">{{ p.name }}</option>
                            {% endif %}{% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية المطلوبة:</label><input type="number" id="m-qty" value="1" min="1" required></div>
                    <div class="form-group"><label>اسم أو كود المسوق المعتمد:</label><input type="text" id="m-code" required placeholder="لحفظ عمولتك"></div>
                    <div class="form-group"><label>اسم الزبون بالكامل:</label><input type="text" id="m-cust" required></div>
                    <div class="form-group"><label>رقم هاتف الزبون:</label><input type="text" id="m-phone" required></div>
                    <div class="form-group"><label>عنوان التوصيل تفصيلياً:</label><input type="text" id="m-address" required></div>
                    <button type="submit" class="btn-orange">تجهيز وإرسال الطلب والعمولة واتساب</button>
                </form>
            </div>
        </div>
    </div>
    <script>
        function filterMProducts() {
            let q = document.getElementById('m-search').value.toLowerCase().trim();
            document.querySelectorAll('.m-card').forEach(card => {
                card.style.display = card.getAttribute('data-name').includes(q) ? '' : 'none';
            });
        }
        function submitMarketerOrder(e) {
            e.preventDefault();
            let sel = document.getElementById('marketer-product-select');
            if(!sel.value) return alert("من فضلك اختر منتج أولاً");
            let prod = sel.value;
            let comm = parseFloat(sel.options[sel.selectedIndex].getAttribute('data-comm'));
            let qty = parseInt(document.getElementById('m-qty').value);
            let code = document.getElementById('m-code').value;
            let cust = document.getElementById('m-cust').value;
            let phone = document.getElementById('m-phone').value;
            let addr = document.getElementById('m-address').value;
            let msg = `🔔 *طلب أونلاين جديد - بوابة مسوقين سينا ستور 401*\\n\\n👤 *المسوق:* ${code}\\n📦 *المنتج:* ${prod}\\n🔢 *الكمية:* ${qty} قطعة\\n💰 *إجمالي عمولتك:* ${comm*qty} ج.م\\n-----------------------------------------\\n🤝 *اسم الزبون:* ${cust}\\n📞 *رقم التلفون:* ${phone}\\n📍 *العنوان:* ${addr}`;
            window.location.href = `https://api.whatsapp.com/send?phone={{ whatsapp }}&text=${encodeURIComponent(msg)}`;
        }
    </script>
</body>
</html>
"""

# --- 3️⃣ شاشة الكاشير والمخزن المركزية ---
HTML_CASHIER = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - شاشة الكاشير والمخزن</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 18px; font-weight: bold; }
        .nav-left-links { display: flex; gap: 8px; align-items: center; }
        .admin-btn { background: #111827; color: white; padding: 8px 15px; border-radius: 6px; font-size: 13px; font-weight: bold; border: 1px solid #374151; text-decoration:none;}
        .logout-btn { background: #ef4444; color: white; padding: 8px 12px; border-radius: 6px; font-size: 12px; font-weight: bold; text-decoration:none; }
        .container { max-width: 1100px; margin: 15px auto; padding: 0 10px; display: flex; flex-direction: column; gap: 15px; }
        .card { background: #262626; padding: 15px; border-radius: 10px; border: 1px solid #404040; box-sizing: border-box; }
        .border-yellow { border-top: 5px solid #eab308; }
        h2 { margin-top: 0; font-size: 16px; margin-bottom: 12px; color: #eab308; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 5px; color: #d4d4d4; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; text-align: right; font-size: 14px; }
        .form-group textarea { height: 70px; resize: none; font-family: inherit; }
        .file-input-wrapper { background: #171717; border: 1px dashed #eab308; padding: 15px; border-radius: 6px; text-align: center; cursor: pointer; color: #eab308; font-size: 13px; font-weight: bold; position: relative; }
        .file-input-wrapper input[type="file"] { position: absolute; left: 0; top: 0; opacity: 0; width: 100%; height: 100%; cursor: pointer; }
        .triple-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
        button { display: block; width: 100%; padding: 12px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; background: #eab308; color: #111827; margin-top: 5px; }
        .table-responsive { width: 100%; overflow-x: auto; background: #262626; border-radius: 8px; border: 1px solid #404040; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; min-width: 500px; }
        th, td { padding: 12px 8px; border-bottom: 1px solid #404040; }
        th { background: #171717; color: #eab308; font-weight: bold; }
        td { color: #e0e0e0; }
        .btn-delete { background:#ef4444; color:white; padding:5px 10px; font-size:11px; border-radius:4px; text-decoration:none; font-weight:bold; display:inline-block; }
    </style>
</head>
<body>
    <nav>
        <h1>🖥️ شاشة الكاشير والمخزن المركزية (PostgreSQL)</h1>
        <div class="nav-left-links">
            <a href="/" class="admin-btn">⬅️ المتجر العام</a>
            <a href="/cashier_logout" class="logout-btn">🔒 قفل اللوحة</a>
        </div>
    </nav>
    <div class="container">
        <div class="card border-yellow">
            <h2>📥 إضافة وتوريد البضائع للمخزن الأونلاين</h2>
            <form action="/add_product" method="POST" id="product-form">
                <div class="form-group"><label>اسم المنتج الفعلي:</label><input type="text" name="name" required placeholder="مثال: تيشرت سينا الفخم"></div>
                <div class="form-group"><label>وصف وتفاصيل المنتج:</label><textarea name="description" placeholder="اكتب هنا مواصفات وتفاصيل الحتة..."></textarea></div>

                <div class="form-group">
                    <label>صورة المنتج:</label>
                    <div class="file-input-wrapper">
                        <span id="file-status">📸 اضغط هنا لاختيار صورة من الاستوديو أو الكاميرا</span>
                        <input type="file" id="image_file" accept="image/*" onchange="compressAndConvertImage()">
                    </div>
                    <input type="hidden" id="image_url" name="image_url">
                </div>

                <div class="triple-grid">
                    <div class="form-group"><label>شراء:</label><input type="number" step="any" name="purchase_price" required placeholder="0"></div>
                    <div class="form-group"><label>بيع:</label><input type="number" step="any" name="selling_price" required placeholder="0"></div>
                    <div class="form-group"><label>العمولة:</label><input type="number" step="any" name="commission" required value="0"></div>
                </div>
                <div class="form-group"><label>الكمية المتوفرة بالمهل:</label><input type="number" name="quantity" value="1" min="1" required></div>
                <button type="submit" id="submit-btn">تثبيت وتوريد للمخزن المركزي أونلاين</button>
            </form>
        </div>

        <div class="card">
            <h2>📦 جرد مخزن المحل الفعلي الحالي أونلاين</h2>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th style="text-align: right; padding-right: 15px;">اسم المنتج</th>
                            <th>سعر البيع</th>
                            <th>العمولة</th>
                            <th>المخزون</th>
                            <th>التحكم</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td style="font-weight: bold; color: white; text-align: right; padding-right: 15px;">{{ p.name }}</td>
                            <td style="color: #eab308; font-weight: bold;">{{ p.selling_price }} ج.م</td>
                            <td style="color: #f97316;">{{ p.commission }} ج.م</td>
                            <td style="font-weight: bold;">{{ p.stock_quantity }} قطع</td>
                            <td><a href="/delete_product/{{ p.name }}" class="btn-delete" onclick="return confirm('هل أنت متأكد من حذف هذا المنتج؟')">حذف ×</a></td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" style="color: #a3a3a3; padding: 20px;">المخزن فارغ تماماً حالياً.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        function compressAndConvertImage() {
            const fileInput = document.getElementById('image_file');
            const hiddenInput = document.getElementById('image_url');
            const statusSpan = document.getElementById('file-status');
            const submitBtn = document.getElementById('submit-btn');
            
            if (fileInput.files && fileInput.files[0]) {
                const file = fileInput.files[0];
                statusSpan.innerText = "⏳ جاري كبس وتقليص حجم الصورة فورياً للشبكة...";
                submitBtn.disabled = true;
                
                const reader = new FileReader();
                reader.onload = function (event) {
                    const img = new Image();
                    img.onload = function () {
                        const canvas = document.createElement('canvas');
                        const MAX_WIDTH = 450; 
                        let width = img.width;
                        let height = img.height;

                        if (width > MAX_WIDTH) {
                            height *= MAX_WIDTH / width;
                            width = MAX_WIDTH;
                        }
                        
                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        const compressedBase64 = canvas.toDataURL('image/jpeg', 0.55);
                        hiddenInput.value = compressedBase64;
                        
                        statusSpan.innerText = "✅ صورة الموبايل جاهزة ومكبوسة للتثبيت!";
                        statusSpan.style.color = "#22c55e";
                        submitBtn.disabled = false;
                    };
                    img.src = event.target.result;
                };
                reader.readAsDataURL(file);
            }
        }
    </script>
</body>
</html>
"""

def fetch_all_products():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT name, description, purchase_price, selling_price, commission, stock_quantity, image_url FROM products ORDER BY id DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.route('/')
def index():
    products = fetch_all_products()
    return render_template_string(HTML_INDEX, products=products, whatsapp=MY_WHATSAPP_NUMBER)

@app.route('/marketers')
def marketers():
    products = fetch_all_products()
    return render_template_string(HTML_MARKETERS, products=products, whatsapp=MY_WHATSAPP_NUMBER)

@app.route('/cashier')
def cashier():
    if not session.get('admin_logged_in'):
        return render_template_string(HTML_LOGIN, error=None)
    products = fetch_all_products()
    return render_template_string(HTML_CASHIER, products=products)

@app.route('/cashier_login', methods=['POST'])
def cashier_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return redirect(url_for('cashier'))
    else:
        return render_template_string(HTML_LOGIN, error="❌ رمز الأمان غير صحيح!")

@app.route('/cashier_logout')
def cashier_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if not session.get('admin_logged_in'):
        return "غير مسموح", 403
        
    name = request.form['name'].strip()
    image_url = request.form['image_url'].strip()
    description = request.form['description'].strip()
    purchase_price = float(request.form['purchase_price'] or 0)
    selling_price = float(request.form['selling_price'] or 0)
    commission = float(request.form['commission'] or 0)
    quantity = int(request.form['quantity'] or 1)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # التحقق مما إذا كان المنتج موجوداً مسبقاً لتحديث الكمية والبيانات
    cur.execute("SELECT stock_quantity, image_url, description FROM products WHERE name = %s;", (name,))
    row = cur.fetchone()
    
    if row:
        new_qty = row[0] + quantity
        final_img = image_url if image_url else row[1]
        final_desc = description if description else row[2]
        cur.execute("""
            UPDATE products 
            SET stock_quantity = %s, purchase_price = %s, selling_price = %s, commission = %s, image_url = %s, description = %s
            WHERE name = %s;
        """, (new_qty, purchase_price, selling_price, commission, final_img, final_desc, name))
    else:
        cur.execute("""
            INSERT INTO products (name, description, purchase_price, selling_price, commission, stock_quantity, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (name, description, purchase_price, selling_price, commission, quantity, image_url))
        
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('cashier'))

@app.route('/delete_product/<string:p_name>')
def delete_product(p_name):
    if not session.get('admin_logged_in'):
        return "غير مسموح", 403
        
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE name = %s;", (p_name,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('cashier'))
