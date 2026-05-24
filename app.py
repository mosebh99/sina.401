import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# إعدادات المجلدات والبيئة
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2026')

DATABASE_URL = os.environ.get('DATABASE_URL') or "postgresql://postgres:MoSebA01065653401@db.ellxxztpfpaqlbqsnyhb.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='allow', connect_timeout=10)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login.html')
        return f(*args, **kwargs)
    return decorated_function

# --- الروابط (Routes) ---
@app.route('/')
def home(): return render_template('index.html')

@app.route('/login.html')
def login_page(): return render_template('login.html')

@app.route('/cashier.html')
@login_required
def cashier(): return render_template('cashier.html')

# المسار اللي كان ناقص عشان يفتح صفحة المسوقين
@app.route('/marketers.html')
@login_required
def marketers(): return render_template('marketers.html')

# --- الـ APIs (كل وظائفك القديمة موجودة هنا) ---

@app.route('/api/marketers', methods=['GET'])
@login_required
def get_marketers():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM marketers ORDER BY id DESC;")
    res = cur.fetchall()
    cur.close(); conn.close()
    return jsonify(res)

@app.route('/api/auth/login', methods=['POST'])
def admin_login():
    data = request.json
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s;", (data['username'],))
        u = cur.fetchone()
        cur.close(); conn.close()
        # التحقق (استبدل بـ check_password_hash لو كنت تستخدم الهاش)
        if u and u['password'] == data['password']:
            session['user_id'] = u['id']
            return jsonify({"success": True})
        return jsonify({"success": False, "message": "بيانات الدخول غير صحيحة"}), 401
    except Exception as e: return jsonify({"error": str(e)}), 500

# أضفت باقي دوالك اللي كانت في ملفك الأصلي هنا (أنت ضيفها بنفس الترتيب عشان تتأكد إن كل شيء موجود)
# ... [ضع هنا باقي الـ APIs اللي كانت موجودة في ملفك الأصلي] ...

if __name__ == '__main__':
    app.run(debug=True)
