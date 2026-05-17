from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json

app = Flask(__name__)
app.secret_key = 'sinai_store_401_secret_key_2026'

MY_WHATSAPP_NUMBER = "201065653401" 
ADMIN_PASSWORD = "010656534"

# الاتصال بقاعدة البيانات باستخدام الرابط التلقائي من فيرسيل
def get_db_connection():
    db_url = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    conn = psycopg2.connect(db_url)
    return conn

# إنشاء الجداول وتحديث الأعمدة تلقائياً لو مش موجودة
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # إنشاء جدول المنتجات مع دعم عمود الأقسام category
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            category VARCHAR(100) DEFAULT 'عام',
            description TEXT,
            purchase_price NUMERIC DEFAULT 0,
            selling_price NUMERIC DEFAULT 0,
            commission NUMERIC DEFAULT 0,
            stock_quantity INTEGER DEFAULT 1,
            image_url TEXT
        );
    """)
    
    # التحقق من وجود عمود category في حالة لو الجدول منشأ قديم لتجنب الـ Errors
    cur.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'عام';
    """)
    
    # إنشاء جدول لحفظ الطلبات المباشرة أونلاين للمسجلين
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            product_name VARCHAR(255),
            quantity INTEGER,
            total_price NUMERIC,
            customer_name VARCHAR(255),
            customer_phone VARCHAR(100),
            customer_address TEXT,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


# --- 1️⃣ صفحة المتجر الرئيسي المتطور ---
HTML_INDEX = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سينا ستور 401 - المتجر الإلكتروني الرسمي</title>
    <meta name="description" content="متجر سينا ستور 401 لبيع أفضل المنتجات والملابس أونلاين بأفضل الأسعار. تسوق الآن واستمتع بشحن سريع ودعم فوري.">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1a1a1a; margin: 0; padding: 0; color: #f3f4f6; }
        nav { background: #eab308; color: #111827; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); position: relative; }
        nav h1 { margin: 0; font-size: 22px; font-weight: bold; }
        .nav-right { display: flex; align-items: center; gap: 15px; position: relative; }
        .auth-status-btn { background: #111827; color: #eab308; border: 1px solid #111827; padding: 8px 12px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 13px; }
        .menu-dots-btn { background: none; border: none; font-size: 24px; cursor: pointer; color: #111827; padding: 0 10px; font-weight: bold; line-height: 1; }
        .dropdown-menu { display: none; position: absolute; left: 0; top: 45px; background: #262626; border: 1px solid #404040; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 100; min-width: 170px; overflow: hidden; }
        .dropdown-menu button { display: block; width: 100%; padding: 12px 15px; color: white; text-decoration: none; background: none; border: none; text-align: right; font-size: 14px; font-family: inherit; cursor: pointer; box-sizing: border-box; border-bottom: 1px solid #333; }
        .dropdown-menu button:hover { background: #404040; color: #eab308; }

        .categories-container { max-width: 1300px; margin: 20px auto 0 auto; padding: 0 20px; box-sizing: border-box; }
        .categories-bar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: thin; }
        .cat-btn { background: #262626; color: #d4d4d4; padding: 8px 16px; border-radius: 20px; border: 1px solid #404040; cursor: pointer; white-space: nowrap; font-weight: 600; font-size: 13px; font-family: inherit; }
        .cat-btn.active { background: #eab308; color: #111827; border-color: #eab308; }

        .main-container { max-width: 1300px; margin: 15px auto 25px auto; padding: 0 20px; display: grid; grid-template-columns: 2fr 1fr; gap: 25px; box-sizing: border-box; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
        
        .search-box { width: 100%; padding: 12px; background: #262626; border: 1px solid #404040; border-radius: 8px; color: white; font-size: 14px; margin-bottom: 20px; box-sizing: border-box; text-align: right; font-family: inherit; }
        .products-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
        .product-card { background: #262626; border: 1px solid #404040; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; flex-direction: column; cursor: pointer; transition: transform 0.2s; }
        .product-card:hover { transform: translateY(-3px); border-color: #eab308; }
        .product-img { width: 100%; height: 180px; object-fit: cover; background: #171717; }
        .product-info { padding: 12px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .product-title { font-size: 15px; font-weight: bold; margin: 0 0 8px 0; color: white; }
        .price-badge-mini { color: #eab308; font-weight: bold; font-size: 15px; margin-bottom: 6px; }
        .stock-count { font-size: 12px; color: #a3a3a3; margin-bottom: 12px; }
        
        .action-card-btn { width: 100%; padding: 8px; border: none; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px; font-family: inherit; }
        .btn-whatsapp { background: #22c55e; color: white; }
        .btn-direct { background: #2563eb; color: white; }

        .order-card { background: #262626; padding: 20px; border-radius: 10px; border: 1px solid #404040; border-top: 5px solid #eab308; height: fit-content; position: sticky; top: 20px; }
        h2 { margin-top: 0; font-size: 17px; margin-bottom: 15px; color: #eab308; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; font-size: 13px; margin-bottom: 6px; color: #d4d4d4; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #171717; border: 1px solid #525252; border-radius: 6px; box-sizing: border-box; color: white; font-size: 14px; text-align: right; }
        .btn-yellow-submit { width: 100%; padding: 12px; background: #eab308; color: #111827; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; }
        .no-img-placeholder { height: 180px; background: #171717; display: flex; align-items: center; justify-content: center; color: #525252; font-size: 40px; }
    
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 200; justify-content: center; align-items: center; padding: 20px; }
        .modal-content { background: #262626; border: 1px solid #404040; border-radius: 12px; width: 100%; max-width: 600px; max-height: 90vh; overflow-y: auto; padding: 20px; position: relative; box-sizing: border-box; }
        .close-modal { position: absolute; top: 15px; left: 15px; font-size: 28px; color: #a3a3a3; cursor: pointer; background: none; border: none; }
        .modal-img { width: 100%; max-height: 280px; object-fit: cover; border-radius: 8px; background: #171717; }
        
        .similar-section { margin-top: 25px; border-top: 1px solid #404040; padding-top: 15px; }
        .similar-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; margin-top: 10px; }
        .similar-card { background: #171717; border: 1px solid #404040; border-radius: 6px; padding: 8px; text-align: center; cursor: pointer; }
        .similar-card img { width: 100%; height: 75px; object-fit: cover; border-radius: 4px; }
        .similar-card h4 { font-size: 12px; margin: 6px 0 3px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: white; }
        .similar-card span { font-size: 11px; color: #eab308; font-weight: bold; }
    </style>
</head>
<body>

    <nav>
        <h1>🦅 سينا ستور 401</h1>
        <div class="nav-right">
            <button id="auth-toggle-btn" onclick="toggleAuthMock()" class="auth-status-btn">🔐 زائر (الشراء عبر واتساب)</button>
            <button onclick="toggleMenu(event)" class="menu-dots-btn">⋮</button>
            <div id="more-dropdown" class="dropdown-menu">
                <button onclick="location.href='/marketers'">👥 بوابة المسوقين</button>
                <button onclick="location.href='/cashier'">🖥️ الكاشير والإدارة</button>
            </div>
        </div>
    </nav>

    <div class="categories-container">
        <div class="categories-bar" id="categories-wrapper"></div>
    </div>

    <div class="main-container">
        <div>
            <input type="text" id="search-input" class="search-box" placeholder="🔍 ابحث عن منتج داخل المتجر...">
            <h2 style="color: #eab308; margin-top: 0;">🛒 المنتجات المتاحة للطلب السريع</h2>
            <div class="products-grid" id="products-container"></div>
        </div>

        <div>
            <div class="order-card" id="sidebar-order-card">
                <h2 id="form-title">🛍️ نموذج الشراء الفوري</h2>
                <form id="customer-order-form" onsubmit="submitCustomerOrder(event)">
                    <div class="form-group">
                        <label>المنتج المطلوب شراءه:</label>
                        <select id="customer-product-select" required></select>
                    </div>
                    <div class="form-group"><label>الكمية:</label><input type="number" id="customer-qty" value="1" min="1" required></div>
                    <div class="form-group"><label>اسمك الكامل:</label><input type="text" id="cust-name" required placeholder="الاسم ثلاثي"></div>
                    <div class="form-group"><label>رقم التليفون / الواتساب:</label><input type="text" id="cust-phone" required></div>
                    <div class="form-group"><label>عنوان شحن الطلب بالتفصيل:</label><input type="text" id="cust-address" required placeholder="المحافظة / المدينة / اسم الشارع"></div>
                    <button type="submit" id="submit-form-btn" class="btn-yellow-submit">📦 إرسال طلب الشراء</button>
                </form>
            </div>
        </div>
    </div>

    <div id="product-modal" class="modal" onclick="closeProductModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <button class="close-modal" onclick="document.getElementById('product-modal').style.display='none'">&times;</button>
            <div id="modal-body-content"></div>
            <div class="similar-section">
                <h3 style="font-size: 13px; color:#eab308; margin: 0 0 10px 0;">📦 منتجات قد تعجبك أيضاً في هذا القسم:</h3>
                <div class="similar-grid" id="similar-products-wrapper"></div>
            </div>
        </div>
    </div>

    <script>
        const MY_WHATSAPP_NUMBER = "{{ whatsapp }}";
        let products = {{ json_products | safe }};
        let isLoggedIn = localStorage.getItem('user_logged_in') === 'true';
        let selectedCategory = "الكل";

        function toggleMenu(e) {
            e.stopPropagation();
            const dropdown = document.getElementById('more-dropdown');
            dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        }
        document.addEventListener('click', () => { document.getElementById('more-dropdown').style.display = 'none'; });

        function toggleAuthMock() {
            isLoggedIn = !isLoggedIn;
            localStorage.setItem('user_logged_in', isLoggedIn);
            updateAuthUI();
            renderStore();
        }

        function updateAuthUI() {
            const btn = document.getElementById('auth-toggle-btn');
            const formTitle = document.getElementById('form-title');
            const submitBtn = document.getElementById('submit-form-btn');
            
            if (isLoggedIn) {
                btn.innerText = "🔓 حساب مسجل (شراء مباشر من الموقع)";
                btn.style.color = "#2563eb";
                formTitle.innerText = "🛍️ نموذج الشراء المباشر (الدفع عند الاستلام)";
                submitBtn.innerText = "📦 تأكيد طلب الشراء الفوري في السيستم";
                
                document.getElementById('cust-name').value = localStorage.getItem('cached_cust_name') || '';
                document.getElementById('cust-phone').value = localStorage.getItem('cached_cust_phone') || '';
                document.getElementById('cust-address').value = localStorage.getItem('cached_cust_address') || '';
            } else {
                btn.innerText = "🔐 زائر (الشراء عبر واتساب)";
                btn.style.color = "#111827";
                formTitle.innerText = "🛍️ نموذج الشراء المباشر للواتساب";
                submitBtn.innerText = "📦 إرسال تفاصيل الطلب للواتساب فوراً";
            }
        }

        function renderCategoriesBar() {
            const wrapper = document.getElementById('categories-wrapper');
            let categories = ["الكل"];
            products.forEach(p => {
                let cat = p.category || "عام";
                if(!categories.includes(cat)) categories.push(cat);
            });
            wrapper.innerHTML = '';
            categories.forEach(cat => {
                const isActive = selectedCategory === cat ? 'active' : '';
                wrapper.innerHTML += `<button class="cat-btn ${isActive}" onclick="filterByCategory('${cat}')">${cat}</button>`;
            });
        }

        function filterByCategory(cat) {
            selectedCategory = cat;
            renderCategoriesBar();
            renderStore();
        }

        function renderStore() {
            const container = document.getElementById('products-container');
            const select = document.getElementById('customer-product-select');
            const searchQuery = document.getElementById('search-input').value.toLowerCase().trim();
            
            container.innerHTML = '';
            select.innerHTML = '<option value="">-- اضغط واختر المنتج المطلوب شراءه --</option>';

            let filteredProducts = products.filter(p => {
                let pCat = p.category || "عام";
                const matchesSearch = p.name.toLowerCase().includes(searchQuery);
                const matchesCategory = selectedCategory === "الكل" || pCat === selectedCategory;
                return matchesSearch && matchesCategory;
            });

            products.forEach(p => {
                if(p.stock_quantity > 0) {
                    select.innerHTML += `<option value="${p.id}">${p.name} - السعر: ${p.selling_price} ج.م</option>`;
                }
            });

            if (filteredProducts.length === 0) {
                container.innerHTML = '<p style="color: #a3a3a3; text-align: center; grid-column: 1/-1;">لا توجد منتجات متوفرة حالياً.</p>';
                return;
            }

            filteredProducts.forEach(p => {
                let imageHtml = p.image_url ? `<img src="${p.image_url}" class="product-img">` : `<div class="no-img-placeholder">📱</div>`;
                let actionButton = '';
                if(p.stock_quantity > 0) {
                    if (isLoggedIn) {
                        actionButton = `<button class="action-card-btn btn-direct" onclick="selectProductForForm(event, ${p.id})">⚡ شراء فوري ومباشر</button>`;
                    } else {
                        actionButton = `<button class="action-card-btn btn-whatsapp" onclick="selectProductForForm(event, ${p.id})">💬 اطلب عبر الواتساب</button>`;
                    }
                }

                container.innerHTML += `
                    <div class="product-card" style="${p.stock_quantity <= 0 ? 'opacity:0.4;' : ''}" onclick="openProductDetail(${p.id})">
                        ${imageHtml}
                        <div class="product-info">
                            <h3 class="product-title">${p.name}</h3>
                            <div>
                                <div class="price-badge-mini">السعر: ${p.selling_price} ج.م</div>
                                <div class="stock-count">${p.stock_quantity <= 0 ? '❌ نفذت الكمية' : `🟢 متوفر في المخزن`}</div>
                                ${actionButton}
                            </div>
                        </div>
                    </div>
                `;
            });
        }

        function selectProductForForm(event, productId) {
            event.stopPropagation();
            document.getElementById('customer-product-select').value = productId;
            document.getElementById('sidebar-order-card').scrollIntoView({ behavior: 'smooth' });
        }

        function openProductDetail(productId) {
            const product = products.find(p => p.id === productId);
            if(!product) return;

            const modal = document.getElementById('product-modal');
            const body = document.getElementById('modal-body-content');
            
            let img = product.image_url ? `<img src="${product.image_url}" class="modal-img">` : `<div class="no-img-placeholder" style="height:240px;">📱</div>`;
            let desc = product.description ? product.description : "لا توجد تفاصيل إضافية لهذا المنتج حالياً.";
            
            body.innerHTML = `
                ${img}
                <h2 style="margin: 15px 0 5px 0; color:white; font-size:20px;">${product.name}</h2>
                <div style="color:#eab308; font-weight:bold; font-size:16px; margin-bottom:15px;">السعر الحالي: ${product.selling_price} ج.م</div>
                <p style="color:#d4d4d4; font-size:14px; line-height:1.6; background:#171717; padding:12px; border-radius:6px; margin:0;">${desc}</p>
            `;

            const similarWrapper = document.getElementById('similar-products-wrapper');
            similarWrapper.innerHTML = '';
            
            let productCat = product.category || "عام";
            let similar = products.filter(p => (p.category || "عام") === productCat && p.id !== product.id && p.stock_quantity > 0).slice(0, 4);
            
            if(similar.length === 0) {
                similarWrapper.innerHTML = '<p style="color:#a3a3a3; font-size:12px;">لا توجد منتجات مشابهة متوفرة حالياً.</p>';
            } else {
                similar.forEach(sp => {
                    let sImg = sp.image_url ? `<img src="${sp.image_url}">` : `<div style="height:75px; background:#262626; display:flex; align-items:center; justify-content:center;">📱</div>`;
                    similarWrapper.innerHTML += `
                        <div class="similar-card" onclick="switchModalProduct(${sp.id})">
                            ${sImg}
                            <h4>${sp.name}</h4>
                            <span>${sp.selling_price} ج.م</span>
                        </div>
                    `;
                });
            }
            modal.style.display = "flex";
        }

        function switchModalProduct(id) {
            document.getElementById('product-modal').style.display = 'none';
            setTimeout(() => { openProductDetail(id); }, 150);
        }

        function closeProductModal(e) {
            if(e.target.id === "product-modal") {
                document.getElementById('product-modal').style.display = 'none';
            }
        }

        function submitCustomerOrder(event) {
            event.preventDefault();
            const pId = parseInt(document.getElementById('customer-product-select').value);
            const qty = parseInt(document.getElementById('customer-qty').value);
            const name = document.getElementById('cust-name').value.trim();
            const phone = document.getElementById('cust-phone').value.trim();
            const address = document.getElementById('cust-address').value.trim();

            if(!pId) { alert("من فضلك اختر منتجاً أولاً!"); return; }

            let product = products.find(p => p.id === pId);
            if (!product) return;
            let totalCost = product.selling_price * qty;

            if (isLoggedIn) {
                localStorage.setItem('cached_cust_name', name);
                localStorage.setItem('cached_cust_phone', phone);
                localStorage.setItem('cached_cust_address', address);

                const orderData = { product_id: pId, product_name: product.name, quantity: qty, total: totalCost, customer_name: name, customer_phone: phone, customer_address: address };
                
                fetch('/api/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData)
                })
                .then(res => res.json())
                .then(data => {
                    alert(`🎉 تم تسجيل طلبك المباشر في قاعدة البيانات بنجاح! إجمالي الحساب: ${totalCost} ج.م.`);
                    location.reload();
                })
                .catch(err => {
                    alert("حدث خطأ أثناء الاتصال بالسيرفر، جرب مرة أخرى.");
                });
            } else {
                let messageText = `🛒 *طلب شراء جديد من المتجر - سينا ستور 401*\\n\\n` +
                                   `📦 *المنتج:* ${product.name}\\n` +
                                   `🔢 *الكمية:* ${qty} قطعة\\n` +
                                   `💰 *إجمالي الحساب:* ${totalCost} ج.م\\n` +
                                   `-----------------------------------------\\n` +
                                   `👤 *اسم العميل:* ${name}\\n` +
                                   `📞 *رقم التواصل:* ${phone}\\n` +
                                   `📍 *العنوان:* ${address}`;
                window.open(`https://api.whatsapp.com/send?phone=${MY_WHATSAPP_NUMBER}&text=${encodeURIComponent(messageText)}`, '_blank');
            }
        }

        document.getElementById('search-input').addEventListener('input', renderStore);
        updateAuthUI();
        renderCategoriesBar();
        renderStore();
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
            <input type="text" id="search-input" class="search-box" placeholder="🔍 ابحث عن منتج لمعرفة عمولته..." oninput="filterProducts()">
            <h2>📦 قائمة بضائع وعمولات الأونلاين الحالية</h2>
            <div class="products-grid">
                {% for p in products %}
                <div class="product-card item-card" data-name="{{ p.name.lower() }}" style="{% if p.stock_quantity <= 0 %}opacity:0.4;{% endif %}">
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
                    <div class="form-group"><label
