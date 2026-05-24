import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request, render_template, redirect, session
from whitenoise import WhiteNoise
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env (مهم جداً للتشغيل المحلي)
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR, prefix='/static/')
app.secret_key = os.environ.get('SECRET_KEY', 'sina-401-secret-key-2026')

# 🛡️ الحماية: جلب الرابط من متغيرات البيئة فقط لمنع اختراق قاعدة البيانات
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("⚠️ خطأ قاتل: لم يتم العثور على DATABASE_URL في البيئة أو ملف .env")
    return psycopg2.connect(DATABASE_URL, sslmode='require', connect_timeout=10)

# ==========================================
# تحديث قاعدة البيانات تلقائياً
# ==========================================

def migrate_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # إضافة الأعمدة الجديدة لجدول الطلبات
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='products_json') THEN
                    ALTER TABLE orders ADD COLUMN products_json TEXT;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='marketer_code') THEN
                    ALTER TABLE orders ADD COLUMN marketer_code VARCHAR(100) DEFAULT '';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='marketer_commission') THEN
                    ALTER TABLE orders ADD COLUMN marketer_commission REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='orders' AND column_name='payment_method') THEN
                    ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50) DEFAULT 'كاش';
                END IF;
            END $$;
        """)
        
        # إضافة الأعمدة المفقودة إلى المنتجات
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='products' AND column_name='commission_egp') THEN
                    ALTER TABLE products ADD COLUMN commission_egp REAL DEFAULT 0;
                END IF;
            END $$;
        """)
        
        # إضافة الأعمدة المفقودة إلى المسوقين
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='marketers' AND column_name='balance') THEN
                    ALTER TABLE marketers ADD COLUMN balance REAL DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='marketers' AND column_name='total_earned') THEN
                    ALTER TABLE marketers ADD COLUMN total_earned REAL DEFAULT 0;
                END IF;
            END $$;
        """)
        
        # إنشاء جدول طلبات السحب
        cur.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id SERIAL PRIMARY KEY,
                marketer_id INTEGER,
                marketer_code VARCHAR(50),
                amount REAL DEFAULT 0,
                vodafone_number VARCHAR(50),
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database migration completed!")
    except Exception as e:
        print(f"Migration error: {e}")

# ==========================================
# إنشاء الجداول الأساسية
# ==========================================

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                description TEXT,
                selling_price REAL DEFAULT 0,
                purchasing_price REAL DEFAULT 0,
                commission_egp REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                image_url TEXT,
                extra_images TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name VARCHAR(255),
                customer_phone VARCHAR(50),
                customer_address TEXT,
                total_price REAL DEFAULT 0,
                products_json TEXT,
                status VARCHAR(50) DEFAULT 'قيد المراجعة',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                marketer_code VARCHAR(100) DEFAULT '',
                marketer_commission REAL DEFAULT 0,
                payment_method VARCHAR(50) DEFAULT 'كاش'
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marketers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(50),
                code VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                commission_rate REAL DEFAULT 0,
                balance REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

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

        conn.commit()

        hashed = generate_password_hash('MoSebA01065653401')
        cursor.execute("""
            INSERT INTO users (username, password, role, name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING;
        """, ('admin', hashed, 'manager', 'المدير'))

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized!")
    except Exception as e:
        print(f"Init error: {e}")

# تشغيل التحديثات عند بدء التشغيل
if DATABASE_URL:
    migrate_database()
    init_database()

# ==========================================
# Middleware
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def manager_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'manager':
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def marketer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
