import os
import json
import psycopg2
import secrets
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session, send_from_directory
from whitenoise import WhiteNoise
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2026')

DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

# ==========================================
# إنشاء وتحديث الجداول (Database Migration)
# ==========================================

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. جدول المنتجات (مع دعم العمولة الثابتة بالجنيه وحالة التفعيل)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                selling_price REAL DEFAULT 0,
                purchasing_price REAL DEFAULT 0,
                commission REAL DEFAULT 0, 
                commission_amount REAL DEFAULT 0,
                commission_enabled BOOLEAN DEFAULT TRUE,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT,
                extra_images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. جدول الطلبات الأساسي
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                marketer_id VARCHAR(100),
                marketer_code VARCHAR(100),
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 3. جدول المسوقين
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                code VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL DEFAULT '',
                commission_rate REAL DEFAULT 0,
                total_sales REAL DEFAULT 0,
                total_commission REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. جدول طلبات الأفلييت (حفظ العمولة الثابتة وقت الشراء لضمان عدم تأثر الطلبات القديمة بالتعديلات المستقبلية)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_orders (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                marketer_code VARCHAR(50) NOT NULL,
                product_id INTEGER,
                product_name VARCHAR(255),
                quantity INTEGER DEFAULT 1,
                commission_per_item REAL DEFAULT 0,
                total_commission REAL DEFAULT 0,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 5. جدول سجل أرباح وحسابات المسوقين
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS affiliate_earnings (
                id SERIAL PRIMARY KEY,
                marketer_code VARCHAR(50) UNIQUE NOT NULL,
                confirmed_earnings REAL DEFAULT 0,
                pending_earnings REAL DEFAULT 0,
                cancelled_earnings REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. سجل العمليات والإشعارات لكل حركة ماليّة
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commission_logs (
                id SERIAL PRIMARY KEY,
                marketer_code VARCHAR(50) NOT NULL,
                order_id INTEGER,
                amount REAL NOT NULL,
                action_type VARCHAR(50), -- 'إضافة عمولة معلقة', 'تأكيد أرباح', 'إلغاء عمولة'
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 7. جدول الإدارة والأدمن
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'admin',
                name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # تأمين التحديثات (Migrations) للأعمدة الجديدة في الجداول القائمة
        cursor.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='products' AND column_name='commission_amount') THEN
                    ALTER TABLE products ADD COLUMN commission_amount REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='products' AND column_name='commission_enabled') THEN
                    ALTER TABLE products ADD COLUMN commission_enabled BOOLEAN DEFAULT TRUE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='products' AND column_name='purchasing_price') THEN
                    ALTER TABLE products ADD COLUMN purchasing_price REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='products' AND column_name='extra_images') THEN
                    ALTER TABLE products ADD COLUMN extra_images TEXT DEFAULT '[]';
                END IF;
            END $$;
        """)

        conn.commit()

        # إضافة حساب الأدمن الافتراضي إذا لم يكن موجوداً
        admin_pass = os.environ.get('ADMIN_PASSWORD', 'MoSebA01065653401')
        hashed = generate_password_hash(admin_pass)
        cursor.execute("""
            INSERT INTO users (username, password, role, name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
        """, ('admin', hashed, 'manager', 'المدير'))

        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized and migrated successfully with fix-commission system!")
    except Exception as e:
        print(f"Database error during initialization: {e}")

init_database()

# الدالة المساعدة لتحديث أرصدة المسوق الذكية بناءً على الحالات
def sync_marketer_balance(marketer_code):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # حساب إجمالي المعلق
        cur.execute("SELECT COALESCE(SUM(total_commission), 0) as amt FROM affiliate_orders WHERE marketer_code = %s AND status = 'قيد المراجعة';", (marketer_code,))
        pending = cur.fetchone()['amt']
        
        # حساب إجمالي المكتمل
        cur.execute("SELECT COALESCE(SUM(total_commission), 0) as amt FROM affiliate_orders WHERE marketer_code = %s AND status = 'تم التسليم';", (marketer_code,))
        confirmed = cur.fetchone()['amt']
        
        # حساب إجمالي الملغي
        cur.execute("SELECT COALESCE(SUM(total_commission), 0) as amt FROM affiliate_orders WHERE marketer_code = %s AND status = 'مرتجع';", (marketer_code,))
        cancelled = cur.fetchone()['amt']
        
        # تحديث أو إنشاء في جدول affiliate_earnings
        cur.execute("""
            INSERT INTO affiliate_earnings (marketer_code, confirmed_earnings, pending_earnings, cancelled_earnings, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (marketer_code) DO UPDATE SET
                confirmed_earnings = EXCLUDED.confirmed_earnings,
                pending_earnings = EXCLUDED.pending_earnings,
                cancelled_earnings = EXCLUDED.cancelled_earnings,
                updated_at = CURRENT_TIMESTAMP;
        """, (marketer_code, confirmed, pending, cancelled))
        
        # تحديث الحقول في جدول المسوقين الرئيسي للمحافظة على التوافق الرجعي
        cur.execute("""
            UPDATE marketers SET 
                total_commission = %s,
                total_sales = (SELECT COALESCE(SUM(orders.total_price), 0) FROM orders WHERE orders.marketer_code = %s AND orders.status = 'تم التسليم')
            WHERE code = %s;
        """, (confirmed, marketer_code, marketer_code))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error syncing marketer balance: {e}")

# ==========================================
# Middleware للصلاحيات
# ==========================================

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        if session.get('role') != 'manager':
            return jsonify({"error": "ليس لديك صلاحية الوصول"}), 403
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        if session.get('role') not in ['manager', 'admin']:
            return jsonify({"error": "ليس لديك صلاحية الوصول"}), 403
        return f(*args, **kwargs)
    return decorated_function

def marketer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'marketer_id' not in session:
            return redirect('/marketer_login.html')
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# مسارات الصفحات
# ==========================================

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/cashier.html')
@admin_required
def cashier_page():
    return render_template('cashier.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

@app.route('/marketers.html')
@admin_required
def marketers_page():
    return render_template('marketers.html')

@app.route('/marketer_login.html')
def marketer_login_page():
    return render_template('marketer_login.html')

@app.route('/marketer_dashboard.html')
@marketer_required
def marketer_dashboard_page():
    return render_template('marketer_dashboard.html')

@app.route('/product_detail.html')
def product_detail_page():
    return render_template('product_detail.html')

# ==========================================
# APIs الحسابات والإدارة
# ==========================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح", "role": user['role'], "name": user['name']})
        return jsonify({"success": False, "message": "بيانات الدخول غير صحيحة"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "تم تسجيل الخروج"})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    return jsonify({"authenticated": 'user_id' in session, "role": session.get('role'), "name": session.get('name')})

@app.route('/api/users', methods=['GET', 'POST'])
@manager_required
def api_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if request.method == 'GET':
            cur.execute("SELECT id, username, role, name, created_at FROM users ORDER BY id DESC;")
            users = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(users)
        elif request.method == 'POST':
            data = request.json
            hashed = generate_password_hash(data.get('password', '123456'))
            cur.execute("""
                INSERT INTO users (username, password, role, name)
                VALUES (%s, %s, %s, %s) RETURNING id, username, role, name, created_at;
            """, (data.get('username'), hashed, data.get('role', 'admin'), data.get('name')))
            new_user = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_user), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@manager_required
def delete_user(uid):
    try:
        if uid == session.get('user_id'):
            return jsonify({"error": "لا يمكن حذف حسابك الحالي"}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s;", (uid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API المنتجات (إضافة/تعديل مع دعم العمولات بالجنيه)
# ==========================================

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
            if 'user_id' not in session or session.get('role') not in ['manager', 'admin']:
                return jsonify({"error": "غير مصرح لك بالإجراء"}), 403
            data = request.json
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO products (name, category, description, selling_price, purchasing_price, commission_amount, commission_enabled, stock_quantity, image_url, extra_images)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                float(data.get('selling_price', 0)), float(data.get('purchasing_price', 0)),
                float(data.get('commission_amount', 0)), data.get('commission_enabled', True),
                int(data.get('stock_quantity', 0)), data.get('image_url'), data.get('extra_images', '[]')
            ))
            new_product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(new_product), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/<int:pid>', methods=['GET', 'PUT', 'DELETE'])
def product_detail(pid):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if request.method == 'GET':
            cur.execute("SELECT * FROM products WHERE id = %s;", (pid,))
            product = cur.fetchone()
            cur.close()
            conn.close()
            if product:
                return jsonify(product)
            return jsonify({"error": "المنتج غير موجود"}), 404

        elif request.method == 'PUT':
            if 'user_id' not in session or session.get('role') not in ['manager', 'admin']:
                return jsonify({"error": "غير مصرح لك بالإجراء"}), 403
            data = request.json
            cur.execute("""
                UPDATE products SET
                    name = %s, category = %s, description = %s,
                    selling_price = %s, purchasing_price = %s,
                    commission_amount = %s, commission_enabled = %s, 
                    stock_quantity = %s, image_url = %s, extra_images = %s
                WHERE id = %s RETURNING *;
            """, (
                data.get('name'), data.get('category'), data.get('description'),
                float(data.get('selling_price', 0)), float(data.get('purchasing_price', 0)),
                float(data.get('commission_amount', 0)), data.get('commission_enabled', True),
                int(data.get('stock_quantity', 0)), data.get('image_url'), data.get('extra_images', '[]'), pid
            ))
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(updated)

        elif request.method == 'DELETE':
            if 'user_id' not in session or session.get('role') not in ['manager', 'admin']:
                return jsonify({"error": "غير مصرح لك بالإجراء"}), 403
            cur.execute("DELETE FROM products WHERE id = %s;", (pid,))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# API الطلبات وإدارة العمولات التلقائية الثابتة بالجنيه
# ==========================================

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

            items_data = data.get('products') or data.get('items') or []
            products_json_str = json.dumps(items_data, ensure_ascii=False)
            total_val = data.get('total_price') or data.get('total_val') or 0
            marketer_code = data.get('marketer_code', '').strip()

            # إدراج الطلب الأساسي أولاً بوضع "قيد المراجعة"
            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, total_price, marketer_code, products_json, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *;
            """, (
                data.get('customer_name'), data.get('customer_phone'), data.get('customer_address'),
                float(total_val), marketer_code, products_json_str, 'قيد المراجعة'
            ))
            new_order = cur.fetchone()
            order_id = new_order['id']

            # إذا تم تقديم الطلب عبر كود مسوق صالح، نقوم بحساب وحفظ العمولات الثابتة فوراً
            if marketer_code:
                cur.execute("SELECT * FROM marketers WHERE code = %s;", (marketer_code,))
                m_profile = cur.fetchone()
                
                if m_profile:
                    for item in items_data:
                        p_id = item.get('id')
                        qty = int(item.get('qty', 1))
                        
                        # سحب قيمة العمولة الحالية للمنتج لمعرفة هل هي مفعلة وما قيمتها الثابتة بالجنيه
                        cur.execute("SELECT commission_amount, commission_enabled FROM products WHERE id = %s;", (p_id,))
                        prod = cur.fetchone()
                        
                        if prod and prod['commission_enabled']:
                            comm_per_item = float(prod['commission_amount'])
                            total_item_comm = comm_per_item * qty
                            
                            # حفظ تفاصيل العمولة ثابتة داخل الطلب (تأمين العمولات القديمة)
                            cur.execute("""
                                INSERT INTO affiliate_orders (order_id, marketer_code, product_id, product_name, quantity, commission_per_item, total_commission, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, 'قيد المراجعة');
                            """, (order_id, marketer_code, p_id, item.get('name'), qty, comm_per_item, total_item_comm))
                            
                            # إدراج سجل العمليات كإشعار للعمولة المعلقة
                            cur.execute("""
                                INSERT INTO commission_logs (marketer_code, order_id, amount, action_type, notes)
                                VALUES (%s, %s, %s, 'إضافة عمولة معلقة', %s);
                            """, (marketer_code, order_id, total_item_comm, f"عمولة معلقة للمنتج {item.get('name')} عدد {qty}"))
            
            conn.commit()
            cur.close()
            conn.close()

            # مزامنة وتحديث رصيد المسوق مباشرة بعد تقديم الطلب
            if marketer_code:
                sync_marketer_balance(marketer_code)

            return jsonify(new_order), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/orders/<int:oid>', methods=['GET', 'PUT', 'DELETE'])
def order_detail(oid):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if request.method == 'GET':
            cur.execute("SELECT * FROM orders WHERE id = %s;", (oid,))
            order = cur.fetchone()
            cur.close()
            conn.close()
            if order:
                return jsonify(order)
            return jsonify({"error": "الطلب غير موجود"}), 404

        elif request.method == 'PUT':
            data = request.json
            new_status = data.get('status').strip() # قيد المراجعة، جاري الشحن، تم التسليم، مرتجع
            
            # سحب كود المسوق المرتبط بالطلب إن وجد
            cur.execute("SELECT marketer_code FROM orders WHERE id = %s;", (oid,))
            order_data = cur.fetchone()
            m_code = order_data['marketer_code'] if order_data else None

            # تحديث حالة الطلب الرئيسي
            cur.execute("UPDATE orders SET status = %s WHERE id = %s RETURNING *;", (new_status, oid))
            updated_order = cur.fetchone()

            if m_code:
                # تحديث حالة العمولات التابعة للطلب في جدول affiliate_orders تلقائياً
                cur.execute("UPDATE affiliate_orders SET status = %s WHERE order_id = %s RETURNING *;", (new_status, oid))
                updated_aff_items = cur.fetchall()

                # تسجيل لوج العمليات والإشعارات المالية بناءً على التغير الجديد للحالة
                for aff_item in updated_aff_items:
                    action = 'تأكيد أرباح' if new_status == 'تم التسليم' else ('إلغاء عمولة' if new_status == 'مرتجع' else 'تعديل حالة العمولة')
                    notes = f"تم نقل عمولة منتج {aff_item['product_name']} إلى حالة {new_status} بناءً على تحديث الأدمن للطلب."
                    
                    cur.execute("""
                        INSERT INTO commission_logs (marketer_code, order_id, amount, action_type, notes)
                        VALUES (%s, %s, %s, %s, %s);
                    """, (m_code, oid, aff_item['total_commission'], action, notes))

            conn.commit()
            cur.close()
            conn.close()

            # إعادة مزامنة وتحديث فوري لأرصدة وأرباح المسوق مباشرة
            if m_code:
                sync_marketer_balance(m_code)

            return jsonify(updated_order)

        elif request.method == 'DELETE':
            # سحب كود المسوق قبل المسح للمزامنة
            cur.execute("SELECT marketer_code FROM orders WHERE id = %s;", (oid,))
            order_data = cur.fetchone()
            m_code = order_data['marketer_code'] if order_data else None

            cur.execute("DELETE FROM orders WHERE id = %s;", (oid,))
            conn.commit()
            cur.close()
            conn.close()

            if m_code:
                sync_marketer_balance(m_code)
            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# APIs حسابات المسوق والـ Dashboard الاحترافي
# ==========================================

@app.route('/api/marketers', methods=['GET', 'POST'])
@admin_required
def api_marketers():
    try:
        conn = get_db_connection()
        if request.method == 'GET':
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, name, phone, code, commission_rate, total_sales, total_commission, created_at FROM marketers ORDER BY id DESC;")
            marketers = cur.fetchall()
            cur.close()
            conn.close()
            return jsonify(marketers)

        elif request.method == 'POST':
            data = request.json
            password = data.get('password', '123456')
            hashed_pass = generate_password_hash(password)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO marketers (name, phone, code, password, commission_rate, total_sales, total_commission)
                VALUES (%s, %s, %s, %s, %s, 0, 0) RETURNING id, name, phone, code, commission_rate, total_sales, total_commission, created_at;
            """, (data.get('name'), data.get('phone'), data.get('code'), hashed_pass, 0))
            new_marketer = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            # إنشاء سجل أرباح أولي مصفّر للمسوق الجديد
            sync_marketer_balance(data.get('code'))
            return jsonify(new_marketer), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketers/<int:mid>', methods=['DELETE'])
@admin_required
def delete_marketer(mid):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM marketers WHERE id = %s;", (mid,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API الإحصائيات الكاملة وعرض المبيعات للمسوق الفردي بالتفصيل
@app.route('/api/marketer/dashboard-stats', methods=['GET'])
@marketer_required
def get_marketer_dashboard_data():
    try:
        code = session.get('marketer_code')
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 1. جلب الأرصدة الثلاثة والأرباح التفصيلية من جدول الأرباح الذكي
        cur.execute("SELECT * FROM affiliate_earnings WHERE marketer_code = %s;", (code,))
        earnings = cur.fetchone()
        if not earnings:
            earnings = {"confirmed_earnings": 0, "pending_earnings": 0, "cancelled_earnings": 0}

        # 2. جلب إجمالي عدد الطلبات
        cur.execute("SELECT COUNT(*) as total_orders FROM orders WHERE marketer_code = %s;", (code,))
        total_orders = cur.fetchone()['total_orders']

        # 3. جلب قائمة العمولات لكل منتج وعدد مرات البيع لكل منتج وإجمالي أرباحه منه
        cur.execute("""
            SELECT 
                p.id, p.name, p.image_url, p.selling_price, p.commission_amount, p.commission_enabled,
                COALESCE(SUM(ao.quantity), 0) as total_qty_sold,
                COALESCE(SUM(ao.total_commission), 0) as total_earned_money
            FROM products p
            LEFT JOIN affiliate_orders ao ON p.id = ao.product_id AND ao.marketer_code = %s
            GROUP BY p.id
            ORDER BY p.id DESC;
        """, (code,))
        products_aff_list = cur.fetchall()

        # 4. جلب سجل الأرباح والطلبات التفصيلية مع الأرباح لكل طلب
        cur.execute("""
            SELECT 
                o.id as order_id, o.customer_name, o.status, o.created_at, o.total_price as order_total,
                COALESCE(SUM(ao.total_commission), 0) as commission_earned_for_order
            FROM orders o
            LEFT JOIN affiliate_orders ao ON o.id = ao.order_id
            WHERE o.marketer_code = %s
            GROUP BY o.id
            ORDER BY o.id DESC;
        """, (code,))
        orders_history = cur.fetchall()

        # 5. جلب سجل الحركة الماليّة والإشعارات الأخيرة
        cur.execute("SELECT * FROM commission_logs WHERE marketer_code = %s ORDER BY id DESC LIMIT 15;", (code,))
        logs = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            "balances": earnings,
            "total_orders": total_orders,
            "products_catalog": products_aff_list,
            "orders_history": orders_history,
            "notifications": logs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# بوابات تسجيل الدخول للمسوقين والـ Auth
# ==========================================

@app.route('/api/marketer/login', methods=['POST'])
def marketer_login():
    data = request.json
    code = data.get('code', '').strip()
    password = data.get('password', '').strip()
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM marketers WHERE code = %s;", (code,))
        marketer = cur.fetchone()
        cur.close()
        conn.close()

        if marketer and check_password_hash(marketer['password'], password):
            session['marketer_id'] = marketer['id']
            session['marketer_code'] = marketer['code']
            session['marketer_name'] = marketer['name']
            return jsonify({"success": True, "message": "تم تسجيل الدخول بنجاح", "code": marketer['code'], "name": marketer['name']})
        return jsonify({"success": False, "message": "كود المسوق أو كلمة المرور غير صحيحة"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marketer/logout', methods=['POST'])
def marketer_logout():
    session.pop('marketer_id', None)
    session.pop('marketer_code', None)
    session.pop('marketer_name', None)
    return jsonify({"success": True, "message": "تم تسجيل الخروج"})

@app.route('/api/marketer/check', methods=['GET'])
def check_marketer_auth():
    return jsonify({"authenticated": 'marketer_id' in session, "code": session.get('marketer_code'), "name": session.get('marketer_name')})

# ==========================================
# لوحة التحكم الرئيسية للأدمن (إحصائيات المبيعات)
# ==========================================

@app.route('/api/stats/dashboard', methods=['GET'])
@admin_required
def dashboard_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total_sales FROM orders;")
        total_sales = cur.fetchone()['total_sales']

        cur.execute("SELECT COUNT(*) as total_orders FROM orders;")
        total_orders = cur.fetchone()['total_orders']

        cur.execute("SELECT COUNT(*) as total_products FROM products;")
        total_products = cur.fetchone()['total_products']

        cur.execute("SELECT COUNT(*) as total_marketers FROM marketers;")
        total_marketers = cur.fetchone()['total_marketers']

        cur.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status;")
        orders_by_status = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify({
            "total_sales": total_sales,
            "total_orders": total_orders,
            "total_products": total_products,
            "total_marketers": total_marketers,
            "orders_by_status": orders_by_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
