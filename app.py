from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import sqlite3
import datetime
import json

app = Flask(__name__)
app.secret_key = 'sinai_store_401_secret_key_2026'

MY_WHATSAPP_NUMBER = "201065653401" 

def init_db():
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            purchase_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            commission REAL NOT NULL,
            stock_quantity INTEGER NOT NULL,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 1️⃣ صفحة المتجر الرئيسي للعملاء والزبائن ---
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - المتجر الإلكتروني</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .nav-links { display: flex; gap: 10px; }
        .nav-btn { background: #111827; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid #374151; }
        .main-container { max-width: 1300px; margin: 25px auto; padding: 0 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .search-box { width: 100%; padding: 12px; background: #262626; border: 1px solid #404040; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 20px; box-sizing: border-box; text-align: right; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
        .product-img { width: 100%; height: 200px; object-fit: cover; background: #171717; }
        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: bold; margin: 0 0 10px 0; color: white; }
        .price-badge { background: #171717; border: 1px solid #eab308; color: #eab308; padding: 8px 10px; border-radius: 5px; font-weight: bold; font-size: 15px; text-align: center; margin-bottom: 10px; }
        .stock-count { font-size: 12px; color: #a3a3a3; text-align: center; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #eab308; height: fit-content; position: sticky; top: 20px; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; color: #eab308; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-yellow-submit { width: 100%; padding: 12px; background: #eab308; color: #111827; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 200px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
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
                <div class="product-card item-card" data-name="{{ p[1].lower() }}" style="{% if p[4] <= 0 %}opacity:0.4;{% endif %}">
                    {% if p[5] %}<img src="{{ p[5] }}" class="product-img">{% else %}<div class="no-img-placeholder">📱</div>{% endif %}
                    <div class="product-info">
                        <h3 class="product-title">{{ p[1] }}</h3>
                        <div>
                            <div class="price-badge">السعر: {{ p[3] }} ج.م</div>
                            <div class="stock-count">{% if p[4] <= 0 %}❌ نفذت الكمية مؤقتاً{% else %}متوفر في المخزن: {{ p[4] }} قطعة{% endif %}</div>
                        </div>
                    </div>
                </div>
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
                            {% for p in products %}{% if p[4] > 0 %}
                            <option value="{{ p[1] }}" data-price="{{ p[3] }}">{{ p[1] }}</option>
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
            let prod = sel.value;
            let price = parseFloat(sel.options[sel.selectedIndex].getAttribute('data-price'));
            let qty = parseInt(document.getElementById('cust-qty').value);
            let name = document.getElementById('cust-name').value;
            let phone = document.getElementById('cust-phone').value;
            let addr = document.getElementById('cust-address').value;
            let msg = `🛒 *طلب شراء جديد من المتجر - سينا ستور 401*\\n\\n📦 *المنتج:* ${prod}\\n🔢 *الكمية:* ${qty} قطعة\\n💰 *الحساب:* ${price*qty} ج.م\\n-----------------------------------------\\n👤 *العميل:* ${name}\\n📞 *الهاتف:* ${phone}\\n📍 *العنوان:* ${addr}`;
            window.open(`https://api.whatsapp.com/send?phone={{ whatsapp }}&text=${encodeURIComponent(msg)}`, '_blank');
        }
    </script>
</body>
</html>
"""

# --- 2️⃣ صفحة بوابة عاديات المسوقين ---
HTML_MARKETERS = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - بوابة المسوقين</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #f97316; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .nav-links { display: flex; gap: 10px; }
        .nav-btn { background: #111827; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; border: 1px solid #374151; }
        .main-container { max-width: 1300px; margin: 25px auto; padding: 0 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        .search-box { width: 100%; padding: 12px; background: #262626; border: 1px solid #404040; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 20px; box-sizing: border-box; text-align: right; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 20px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
        .product-img { width: 100%; height: 200px; object-fit: cover; background: #171717; }
        .product-info { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 16px; font-weight: bold; margin: 0 0 10px 0; color: white; }
        .price-badge { background: #171717; border: 1px solid #f97316; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 8px; }
        .comm-badge { background: #ffedd5; color: #c2410c; padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 14px; text-align: center; margin-bottom: 10px; border: 1px solid #f97316; }
        .stock-count { font-size: 12px; color: #a3a3a3; text-align: center; }
        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #f97316; height: fit-content; position: sticky; top: 20px; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; color: #f97316; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-orange { width: 100%; padding: 12px; background: #f97316; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 200px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
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
                <div class="product-card m-card" data-name="{{ p[1].lower() }}" style="{% if p[4] <= 0 %}opacity:0.4;{% endif %}">
                    {% if p[5] %}<img src="{{ p[5] }}" class="product-img">{% else %}<div class="no-img-placeholder">📱</div>{% endif %}
                    <div class="product-info">
                        <h3 class="product-title">{{ p[1] }}</h3>
                        <div>
                            <div class="price-badge">💰 سعر الزبون: {{ p[3] }} ج.م</div>
                            <div class="comm-badge">🎁 عمولتك الصافية: {{ p[2] }} ج.م</div>
                            <div class="stock-count">{% if p[4] <= 0 %}❌ عجز مخزون{% else %}المتاح جردياً: {{ p[4] }} قطعة{% endif %}</div>
                        </div>
                    </div>
                </div>
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
                            {% for p in products %}{% if p[4] > 0 %}
                            <option value="{{ p[1] }}" data-comm="{{ p[2] }}">{{ p[1] }}</option>
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
            let prod = sel.value;
            let comm = parseFloat(sel.options[sel.selectedIndex].getAttribute('data-comm'));
            let qty = parseInt(document.getElementById('m-qty').value);
            let code = document.getElementById('m-code').value;
            let cust = document.getElementById('m-cust').value;
            let phone = document.getElementById('m-phone').value;
            let addr = document.getElementById('m-address').value;
            let msg = `🔔 *طلب أونلاين جديد - بوابة مسوقين سينا ستور 401*\\n\\n👤 *المسوق:* ${code}\\n📦 *المنتج:* ${prod}\\n🔢 *الكمية:* ${qty} قطعة\\n💰 *إجمالي عمولتك:* ${comm*qty} ج.م\\n-----------------------------------------\\n🤝 *اسم الزبون:* ${cust}\\n📞 *رقم التلفون:* ${phone}\\n📍 *العنوان:* ${addr}`;
            window.open(`https://api.whatsapp.com/send?phone={{ whatsapp }}&text=${encodeURIComponent(msg)}`, '_blank');
        }
    </script>
</body>
</html>
"""

# --- 3️⃣ صفحة الكاشير المركزي والجرد ---
HTML_CASHIER = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - شاشة الكاشير والمخزن</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        nav h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .nav-actions { display: flex; align-items: center; gap: 11px; }
        .admin-btn { background: #111827; color: white; padding: 8px 15px; border-radius: 6px; font-size: 13px; font-weight: bold; border: 1px solid #374151; text-decoration:none;}
        .container { max-width: 1350px; margin: 25px auto; padding: 0 20px; display: grid; grid-template-columns: 1.2fr 2fr; gap: 25px; }
        .card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; margin-bottom: 20px; }
        .border-yellow { border-top: 5px solid #eab308; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; }
        .form-group input { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; text-align: right; }
        .triple-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
        button { display: block; width: 100%; padding: 12px; font-weight: bold; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; background: #eab308; color: #111827; }
        table { width: 100%; border-collapse: collapse; text-align: right; font-size: 13px; background: #262626; margin-top: 15px; }
        th, td { padding: 10px; border: 1px solid #404040; }
        th { background: #171717; color: #eab308; }
    </style>
</head>
<body>
    <nav>
        <h1>🖥️ شاشة الكاشير والمخزن المركزية</h1>
        <div class="nav-actions"><a href="/" class="admin-btn">⬅️ المتجر العام</a></div>
    </nav>
    <div class="container">
        <div>
            <div class="card border-yellow">
                <h2>📥 إضافة وتوريد البضائع للمخزن الأونلاين</h2>
                <form action="/add_product" method="POST">
                    <div class="form-group"><label>اسم المنتج الفعلي:</label><input type="text" name="name" required></div>
                    <div class="form-group"><label>رابط الصورة أونلاين:</label><input type="url" name="image_url"></div>
                    <div class="triple-grid">
                        <div class="form-group"><label>شراء:</label><input type="number" step="any" name="purchase_price" required></div>
                        <div class="form-group"><label>بيع:</label><input type="number" step="any" name="selling_price" required></div>
                        <div class="form-group"><label>العمولة:</label><input type="number" step="any" name="commission" required value="0"></div>
                    </div>
                    <div class="form-group"><label>الكمية:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <button type="submit">تثبيت وتوريد للمخزن المركزي أونلاين</button>
                </form>
            </div>
        </div>
        <div>
            <div class="card">
                <h2>📦 جرد مخزن المحل الفعلي الحالي أونلاين</h2>
                <table>
                    <thead>
                        <tr>
                            <th>اسم المنتج</th>
                            <th>سعر البيع</th>
                            <th>العمولة</th>
                            <th>المخزون الحالي</th>
                            <th>التحكم</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for p in products %}
                        <tr>
                            <td style="font-weight: bold; color: white;">{{ p[1] }}</td>
                            <td style="color: #eab308; font-weight: bold;">{{ p[3] }} ج.م</td>
                            <td style="color: #f97316;">{{ p[2] }} ج.م</td>
                            <td>{{ p[4] }} قطعة</td>
                            <td><a href="/delete_product/{{ p[0] }}" style="background:#ef4444; color:white; padding:4px 8px; font-size:11px; border-radius:4px; text-decoration:none;">حذف</a></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, commission, selling_price, stock_quantity, image_url FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_INDEX, products=products, whatsapp=MY_WHATSAPP_NUMBER)

@app.route('/marketers')
def marketers():
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, commission, selling_price, stock_quantity, image_url FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_MARKETERS, products=products, whatsapp=MY_WHATSAPP_NUMBER)

@app.route('/cashier')
def cashier():
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, commission, selling_price, stock_quantity FROM products')
    products = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_CASHIER, products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name'].strip()
    image_url = request.form['image_url'].strip()
    purchase_price = float(request.form['purchase_price'])
    selling_price = float(request.form['selling_price'])
    commission = float(request.form['commission'])
    quantity = int(request.form['quantity'])
    
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO products (name, purchase_price, selling_price, commission, stock_quantity, image_url) VALUES (?, ?, ?, ?, ?, ?)', (name, purchase_price, selling_price, commission, quantity, image_url))
    except:
        cursor.execute('UPDATE products SET stock_quantity = stock_quantity + ?, purchase_price=?, selling_price=?, commission=?, image_url=? WHERE name=?', (quantity, purchase_price, selling_price, commission, image_url, name))
    conn.commit()
    conn.close()
    return redirect(url_for('cashier'))

@app.route('/delete_product/<int:p_id>')
def delete_product(p_id):
    conn = sqlite3.connect('/tmp/store_sinai_401.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products WHERE id=?', (p_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('cashier'))
