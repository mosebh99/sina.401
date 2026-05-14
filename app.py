from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import sqlite3
import datetime
import urllib.parse

app = Flask(__name__)
app.secret_key = 'super_secure_unlocked_system_2026_sinai_v5_final'

# رقم الواتساب المحدث لاستلام طلبات الأونلاين
MY_WHATSAPP_NUMBER = "201065653401" 

def init_db():
    conn = sqlite3.connect('store_sinai_401_commission.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            purchase_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            commission REAL NOT NULL, -- خانة عمولة المسوق المحددة لكل منتج
            stock_quantity INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            cost_price REAL NOT NULL,
            date TEXT NOT NULL,
            user_by TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - الإدارة والأونلاين</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6; margin: 0; padding: 0; color: #333; }
        nav { background: #4f46e5; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .nav-title h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .nav-title span { font-size: 12px; color: #c7d2fe; }
        .nav-actions { display: flex; align-items: center; gap: 15px; }
        .cash-badge { background: #312e81; padding: 8px 15px; border-radius: 6px; font-size: 14px; font-weight: bold; }
        .admin-btn { background: #111827; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }
        .logout-btn { background: #ef4444; color: white; padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: bold; }
        
        .container { max-width: 1300px; margin: 25px auto; padding: 0 20px; display: grid; grid-template-columns: 1fr 2fr; gap: 25px; }
        @media (max-width: 900px) { .container { grid-template-columns: 1fr; } }
        
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .border-green { border-top: 5px solid #10b981; }
        .border-blue { border-top: 5px solid #3b82f6; }
        .border-orange { border-top: 5px solid #f97316; }
        .border-indigo { border-top: 5px solid #4f46e5; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; }
        .text-green { color: #10b981; } .text-blue { color: #3b82f6; } .text-orange { color: #f97316; } .text-indigo { color: #4f46e5; }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; font-weight: 600; color: #4b5563; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; text-align: right; font-size: 14px; }
        
        .flex-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .triple-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
        button, .btn-link { display: block; width: 100%; padding: 12px; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; text-align: center; text-decoration: none; box-sizing: border-box; }
        .btn-green { background: #10b981; }
        .btn-blue { background: #3b82f6; }
        .btn-orange { background: #f97316; }
        .btn-indigo { background: #4f46e5; }
        
        table { width: 100%; border-collapse: collapse; text-align: right; font-size: 13px; margin-top: 10px; background: white; }
        th, td { padding: 12px; border: 1px solid #e5e7eb; }
        th { background: #f3f4f6; color: #4b5563; }
        
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
        .badge-purple { background: #f3e8ff; color: #7e22ce; }
        .badge-orange { background: #ffedd5; color: #c2410c; }
        .alert { background: #fee2e2; color: #991b1b; padding: 12px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; border-right: 4px solid #ef4444; }
        .alert-success { background: #d1fae5; color: #065f46; border-right-color: #10b981; }
        .whatsapp-box { background: #e8f5e9; border: 1px solid #c8e6c9; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-right: 5px solid #25d366; }
        .admin-lock-box { background: #fffbeb; border: 1px solid #fef3c7; border-right: 5px solid #d97706; color: #92400e; padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-size: 14px; }
        
        .summary-box { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 10px; }
        .sum-item { padding: 15px; border-radius: 8px; text-align: center; color: white; font-weight: bold; }
        
        @media print {
            nav, .card, .admin-btn, .logout-btn, button, .whatsapp-box, .admin-lock-box { display: none !important; }
            .container { grid-template-columns: 1fr !important; width: 100% !important; margin: 0 !important; padding: 0 !important; }
            .sum-item { color: black !important; border: 1px solid #333 !important; }
        }
    </style>
</head>
<body>

    <nav>
        <div class="nav-title">
            <h1>🦅 سينا ستور 401</h1>
            <span>الوضع الحالي: <b>{% if session.get('is_admin') %}🔒 لوحة الإدارة مفعّلة{% else %}🔓 بوابة المبيعات العامة والمسوقين{% endif %}</b></span>
        </div>
        <div class="nav-actions">
            {% if session.get('is_admin') %}
                <div class="cash-badge">💸 رصيد الصندوق الإجمالي: {{ "%.2f"|format(cash_register) }} ج.م</div>
                <a href="/logout_admin" class="logout-btn">إغلاق وضع المدير</a>
            {% else %}
                <a href="/login_page" class="admin-btn">⚙️ دخول المدير (للتعديل والتقارير)</a>
            {% endif %}
        </div>
    </nav>

    <div class="container">
        <div>
            {% with messages = get_flashed_messages() %}
              {% if messages %}<div class="alert alert-success">{{ messages }}</div>{% endif %}
            {% endwith %}

            {% if session['whatsapp_url'] %}
            <div class="whatsapp-box">
                <h3 style="margin-top:0; color:#2e7d32; font-size:15px;">🚀 جهزنا طلب الأونلاين بنجاح!</h3>
                <p style="font-size:12px; margin-bottom:10px;">اضغط على الزر ليقوم النظام بفتح الواتساب وإرسال تفاصيل العميل والعمولة فوراً.</p>
                <a href="{{ session['whatsapp_url'] }}" target="_blank" class="btn-link" style="background:#25d366;">🟢 إرسال الطلب عبر WhatsApp الآن</a>
            </div>
            {% endif %}

            <!-- 1. واجهة المسوقين أونلاين (مفتوحة دائماً وبها حساب آلي للعمولة) -->
            <div class="card border-orange">
                <h2 class="text-orange">📣 قسم الأونلاين والمسوقين (إرسال طلب)</h2>
                <form action="/submit_online_order" method="POST">
                    <div class="form-group">
                        <label>اختر المنتج المطلوب بالاسم:</label>
                        <select name="product_id" required>
                            <option value="">-- اضغط واكتب اسم المنتج --</option>
                            {% for prod in products %}
                                <option value="{{ prod }}">{{ prod }} (المتاح: {{ prod }} قطعة) - العمولة: {{ prod }} ج.م</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية المطلوبة:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <div class="form-group"><label>اسم أو كود المسوق:</label><input type="text" name="marketer_name" required placeholder="اكتب اسمك هنا لحفظ عمولتك"></div>
                    <div class="form-group"><label>اسم العميل بالكامل:</label><input type="text" name="customer_name" required></div>
                    <div class="form-group"><label>رقم هاتف العميل:</label><input type="text" name="customer_phone" required></div>
                    <div class="form-group"><label>عنوان التوصيل تفصيلياً:</label><input type="text" name="customer_address" required></div>
                    <button type="submit" class="btn-orange">تجهيز وإرسال الطلب والعمولة واتساب</button>
                </form>
            </div>

            <!-- 2. كاشير البيع الفوري بالمحل -->
            <div class="card border-green">
                <h2 class="text-green">🛒 كاشير البيع الفوري (كاشير المحل المباشر)</h2>
                <form action="/sell" method="POST">
                    <div class="form-group">
                        <label>اختر المنتج المبيع بالاسم:</label>
                        <select name="product_id" required>
                            <option value="">-- اختر المنتج من المخزن --</option>
                            {% for prod in products %}
                                {% if prod > 0 %}
                                <option value="{{ prod }}">{{ prod }} - السعر: {{ prod }} ج.م</option>
                                {% endif %}
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group"><label>الكمية المبيعة جردياً:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <button type="submit" class="btn-green">تأكيد ونفاذ البيع الفوري</button>
                </form>
            </div>

            <!-- 3. توريد البضائع والأسعار وعمولة السيلز (محمي للمدير) -->
            <div class="card border-blue">
                <h2 class="text-blue">📥 توريد بضاعة جديدة / تعديل الأسعار والعمولات</h2>
                {% if session.get('is_admin') %}
                <form action="/save_product" method="POST">
                    <div class="form-group"><label>اسم المنتج ومواصفاته الفنية:</label><input type="text" name="name" required placeholder="مثال: iPhone 15 Pro Max"></div>
                    <div class="form-group">
                        <label>التصنيف الإداري:</label>
                        <select name="category"><option value="هاتف">هاتف محمول</option><option value="إكسسوار">إكسسوار</option></select>
                    </div>
                    <div class="triple-grid">
                        <div class="form-group"><label>سعر الشراء:</label><input type="number" step="0.01" name="purchase_price" required></div>
                        <div class="form-group"><label>سعر البيع:</label><input type="number" step="0.01" name="selling_price" required></div>
                        <div class="form-group"><label>عمولة المسوق (ج.م):</label><input type="number" step="0.01" name="commission" required value="0"></div>
                    </div>
                    <div class="form-group"><label>الكمية الموردة:</label><input type="number" name="quantity" value="1" min="1" required></div>
                    <button type="submit" class="btn-blue">تأكيد الحفظ بالمخزن والعمولة</button>
                </form>
                {% else %}
                <div class="admin-lock-box">
                    🔒 <b>هذا القسم محمي للمدير!</b> سجل دخولك من الأعلى لإضافة بضاعة وتحديد العمولات والأسعار.
                </div>
                {% endif %}
            </div>
        </div>

        <!-- الجانب الأيسر: التقارير والطباعة وجرد المخازن -->
        <div>
            <!-- قسم التقرير والملخص اليومي للطباعة -->
            <div class="card border-indigo">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2 class="text-indigo" style="margin:0;">📊 ملخص البيانات المالي اليومي: {{ current_day }}</h2>
                    {% if session.get('is_admin') %}
                    <button onclick="window.print()" class="btn-indigo" style="width: auto; padding: 6px 15px; font-size: 13px;">🖨️ طباعة التقرير اليومي</button>
                    {% endif %}
                </div>
                
                {% if session.get('is_admin') %}
                <div class="summary-box">
                    <div class="sum-item" style="background: #3b82f6;">
                        <span style="font-size: 11px; display:block;">مشتريات اليوم</span>
                        <span style="font-size: 16px;">{{ "%.2f"|format(day_purchases) }} ج.م</span>
                    </div>
                    <div class="sum-item" style="background: #10b981;">
                        <span style="font-size: 11px; display:block;">مبيعات اليوم</span>
                        <span style="font-size: 16px;">{{ "%.2f"|format(day_sales) }} ج.م</span>
                    </div>
                    <div class="sum-item" style="background: #4f46e5;">
                        <span style="font-size: 11px; display:block;">صافي أرباح اليوم النظري</span>
                        <span style="font-size: 16px;">{{ "%.2f"|format(day_profits) }} ج.م</span>
                    </div>
                </div>
                {% else %}
                <div class="admin-lock-box" style="margin-bottom:0;">
                    🔒 <b>الملخص المالي والربحي محجوب!</b> سجل دخول المدير لتوليد أرقام الأرباح والتمكن من طباعتها ورقياً.
                </div>
                {% endif %}
            </div>

            <!-- جدول جرد المخزن وعرض العمولات أمام المسوقين -->
            <div class="card">
                <h2>📦 جرد رصيد مخزن سينا ستور وعمولات الأونلاين الحالية</h2>
                <table>
                    <thead>
                        <tr>
                            <th>رقم تلقائي</th>
                            <th>اسم المنتج ومواصفاته</th>
                            <th>التصنيف</th>
                            {% if session.get('is_admin') %}<th>سعر الشراء</th>{% endif %}
                            <th>سعر البيع للجمهور</th>
                            <th>عمولة الأونلاين</th>
                            <th>المخزون المتاح</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for prod in products %}
                        <tr>
                            <td style="color: #6b7280; font-family: monospace;">#{{ prod }}</td>
                            <td style="font-weight: bold; color: #111827;">{{ prod }}</td>
                            <td><span class="badge {{ 'badge-purple' if prod=='هاتف' else 'badge-orange' }}">{{ prod }}</span></td>
                            {% if session.get('is_admin') %}<td style="color: #6b7280;">{{ prod }} ج.م</td>{% endif %}
                            <td style="font-weight: bold; color: #10b981;">{{ prod }} ج.م</td>
                            <td style="font-weight: bold; color: #f97316;">{{ prod }} ج.م لكل قطعة</td>
                            <td style="font-weight: bold; color: {{ '#ef4444' if prod == 0 else '#111827' }}">{{ prod }} قطعة</td>
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

# شاشة تسجيل دخول المدير الثابتة ببياناتك
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تسجيل دخول الإدارة</title>
    <style>
        body { font-family: Arial, sans-serif; background: #111827; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .login-box { background: white; padding: 35px; border-radius: 12px; width: 100%; max-width: 350px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 5px; font-weight: bold; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; text-align: right; }
        button { width: 100%; padding: 12px; color: white; background: #4f46e5; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .back-link { display: block; text-align: center; margin-top: 15px; color: #4f46e5; text-decoration: none; font-size: 13px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2 style="text-align: center; margin-bottom: 20px;">🔒 نظام حماية سينا ستور 401</h2>
        <form action="/process_admin_login" method="POST">
            <div class="form-group"><label>اسم مستخدم المدير:</label><input type="text" name="username" required></div>
            <div class="form-group"><label>كلمة المرور السرية:</label><input type="password" name="password" required></div>
            <button type="submit">تفعيل وضع الإدارة والتقارير</button>
        </form>
        <a href="/" class="back-link">← العودة للوحة العامة</a>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    conn = sqlite3.connect('store_sinai_401_commission.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    sales = 0.0
    purchases = 0.0
    if session.get('is_admin'):
        cursor.execute("SELECT SUM(quantity * price) FROM transactions WHERE type='بيع'")
        sales_res = cursor.fetchone()
        sales = sales_res if sales_res is not None else 0.0
        cursor.execute("SELECT SUM(quantity * price) FROM transactions WHERE type='شراء'")
        purchases_res = cursor.fetchone()
        purchases = purchases_res if purchases_res is not None else 0.0
        
    cash_register = sales - purchases
    
    cursor.execute("SELECT SUM(quantity * price) FROM transactions WHERE type='بيع' AND date LIKE ?", (today_str + '%',))
    day_sales = cursor.fetchone() or 0.0
    cursor.execute("SELECT SUM(quantity * price) FROM transactions WHERE type='شراء' AND date LIKE ?", (today_str + '%',))
    day_purchases = cursor.fetchone() or 0.0
    cursor.execute("SELECT SUM((price - cost_price) * quantity) FROM transactions WHERE type='بيع' AND date LIKE ?", (today_str + '%',))
    day_profits = cursor.fetchone() or 0.0
    
    conn.close()
    return render_template_string(HTML_TEMPLATE, products=products, cash_register=cash_register, 
                                  day_sales=day_sales, day_purchases=day_purchases, day_profits=day_profits,
                                  current_day=today_str)

@app.route('/login_page')
def login_page():
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/process_admin_login', methods=['POST'])
def process_admin_login():
    username = request.form['username']
    password = request.form['password']
    if username == "moseba99" and password == "010656534":
        session['is_admin'] = True
        flash('🔓 مرحباً بك يا مدير سينا ستور، تم تفعيل صلاحيات الإدارة الكاملة وجداول الأرباح والعمولات.')
        return redirect(url_for('index'))
    else:
        return "<script>alert('خطأ: بيانات دخول المدير غير صحيحة!'); window.location='/login_page';</script>"

@app.route('/logout_admin')
def logout_admin():
    session['is_admin'] = False
    return redirect(url_for('index'))

@app.route('/submit_online_order', methods=['POST'])
def submit_online_order():
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])
    marketer_name = request.form['marketer_name'].strip()
    customer_name = request.form['customer_name'].strip()
    customer_phone = request.form['customer_phone'].strip()
    customer_address = request.form['customer_address'].strip()
    
    conn = sqlite3.connect('store_sinai_401_commission.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, commission FROM products WHERE id = ?', (product_id,))
    prod = cursor.fetchone()
    conn.close()
    
    if prod:
        product_name, comm_per_piece = prod, prod
        # حساب إجمالي عمولة المسوق بناءً على الكمية المطلوبة تلقائياً
        total_commission = comm_per_piece * quantity
        
        message_text = (
            f"🔔 *طلب أونلاين جديد - سينا ستور 401*\n\n"
            f"👤 *اسم المسوق:* {marketer_name}\n"
            f"📦 *المنتج المطلوب:* {product_name}\n"
            f"🔢 *الكمية:* {quantity} قطعة\n"
            f"💰 *إجمالي عمولة المسوق:* {total_commission} ج.م\n"
            f"-----------------------------------------\n"
            f"🤝 *اسم العميل:* {customer_name}\n"
            f"📞 *رقم التلفون:* {customer_phone}\n"
            f"📍 *العنوان لوكيشن:* {customer_address}\n"
            f"⏰ *التوقيت:* {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        encoded_message = urllib.parse.quote(message_text)
        session['whatsapp_url'] = f"whatsapp.com{MY_WHATSAPP_NUMBER}&text={encoded_message}"
        flash('✅ تم إعداد بيانات الطلب والعمولة بنجاح! اضغط على زر الواتساب الأخضر المتاح بالأسفل لإرسالها.')
    return redirect(url_for('index'))

@app.route('/sell', methods=['POST'])
def sell():
    product_id = int(request.form['product_id'])
    quantity = int(request.form['quantity'])
    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('store_sinai_401_commission.db')
    cursor = conn.cursor()
    cursor.execute('SELECT stock_quantity, selling_price, purchase_price FROM products WHERE id = ?', (product_id,))
    row = cursor.fetchone()
    if row and row[0] >= quantity:
        new_qty = row[0] - quantity
        cursor.execute('UPDATE products SET stock_quantity = ? WHERE id = ?', (new_qty, product_id))
        cursor.execute('INSERT INTO transactions (type, product_id, quantity, price, cost_price, date, user_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       ('بيع', product_id, quantity, row[1], row[2], date_now, 'كاشير المحل'))
        conn.commit()
        flash('✅ تم تأكيد عملية البيع الفوري وخصم الكمية وتحديث أرباح التقرير اليومي.')
    else:
        flash('❌ خطأ: الكمية المطلوبة غير متوفرة في مخزن سينا ستور!')
    conn.close()
    return redirect(url_for('index'))

@app.route('/save_product', methods=['POST'])
def save_product():
    if not session.get('is_admin'): return redirect(url_for('index'))
    name = request.form['name'].strip()
    category = request.form['category']
    purchase_price = float(request.form['purchase_price'])
    selling_price = float(request.form['selling_price'])
    commission = float(request.form['commission'])
    quantity = int(request.form['quantity'])
    date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('store_sinai_401_commission.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, stock_quantity FROM products WHERE name = ?', (name,))
    row = cursor.fetchone()
    if row:
        p_id, current_stock = row[0], row[1]
        new_qty = current_stock + quantity
        cursor.execute('UPDATE products SET stock_quantity = ?, purchase_price = ?, selling_price = ?, commission = ? WHERE id = ?', (new_qty, purchase_price, selling_price, commission, p_id))
    else:
        cursor.execute('INSERT INTO products (name, category, purchase_price, selling_price, commission, stock_quantity) VALUES (?, ?, ?, ?, ?, ?)', (name, category, purchase_price, selling_price, commission, quantity))
        p_id = cursor.lastrowid
    cursor.execute('INSERT INTO transactions (type, product_id, quantity, price, cost_price, date, user_by) VALUES (?, ?, ?, ?, ?, ?, ?)', ('شراء', p_id, quantity, purchase_price, purchase_price, date_now, 'المدير'))
    conn.commit()
    conn.close()
    flash('✅ تم حفظ المنتج المورد وتثبيت قيمة عمولة المسوق أونلاين بنجاح.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
