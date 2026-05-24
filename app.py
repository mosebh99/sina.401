import os
import json
import psycopg2
import secrets
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session
from whitenoise import WhiteNoise
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# إعدادات المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2026')

DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

# الحماية
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

# --- المسارات الأساسية (Routes) ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login.html')
def login_page(): return render_template('login.html')

@app.route('/cashier.html')
@admin_required
def cashier(): return render_template('cashier.html')

@app.route('/marketers.html')
@admin_required
def marketers(): return render_template('marketers.html')

# --- الـ APIs (كل وظائفك القديمة والجديدة) ---

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    data = request.json
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s;", (data['username'],))
        u = cur.fetchone()
        cur.close(); conn.close()
        if u and u['password'] == data['password']:
            session['user_id'] = u['id']
            session['username'] = u['username']
            session['role'] = u['role']
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "بيانات الدخول غير صحيحة"}), 401
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/api/stats/dashboard', methods=['GET'])
@admin_required
def dashboard_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COALESCE(SUM(total_price), 0) as total_sales FROM orders;")
        sales = cur.fetchone()['total_sales']
        cur.execute("SELECT COUNT(*) as c FROM orders;"); o_cnt = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM products;"); p_cnt = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) as c FROM marketers;"); m_cnt = cur.fetchone()['c']
        cur.close(); conn.close()
        return jsonify({"total_sales": sales, "total_orders": o_cnt, "total_products": p_cnt, "total_marketers": m_cnt})
    except Exception as e: return jsonify({"error": str(e)}), 500

# (تأكد من إضافة بقية دوال الـ /api الخاصة بك هنا تحت نفس النمط)

if __name__ == '__main__':
    app.run(debug=True)
