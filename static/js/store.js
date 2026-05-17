let allProducts = [];
let cart = JSON.parse(localStorage.getItem('sinaa_cart')) || [];

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('products-container')) {
        loadStoreProducts();
    }
    updateCartUI();
});

function showToast(msg) {
    const toast = document.getElementById('toast-notification');
    if(toast) {
        toast.innerText = msg;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }
}

async function loadStoreProducts() {
    try {
        const res = await fetch('/api/products');
        allProducts = await res.json();
        renderProducts(allProducts);
    } catch (err) {
        console.error("خطأ في جلب المنتجات:", err);
        const container = document.getElementById('products-container');
        if(container) {
            container.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color: red;">❌ فشل الاتصال بالمخزن السحابي.</p>`;
        }
    }
}

function renderProducts(products) {
    const container = document.getElementById('products-container');
    if(!container) return;
    container.innerHTML = '';
    
    if(products.length === 0) {
        container.innerHTML = `<p style="grid-column: 1/-1; text-align:center; color: var(--text-muted);">لم نجد منتجات تطابق البحث الحالي.</p>`;
        return;
    }

    products.forEach(p => {
        // حماية مسار الصورة الأصلي المتوافق مع الفلاسك وسوبابيس
        let imgSrc = p.image_url || '/static/css/logo.png.jpeg';
        
        container.innerHTML += `
            <div class="product-card">
                <img src="${imgSrc}" loading="lazy" alt="${p.name}" onerror="this.src='/static/css/logo.png.jpeg'">
                <div class="card-body">
                    <h3><a href="/product/${p.id}">${p.name}</a></h3>
                    <p style="color: var(--text-muted); font-size:13px; margin: 0 0 10px 0;">${p.category || 'عام'}</p>
                    <div class="price-box">${p.selling_price || 0} ج.م</div>
                    <button class="btn-primary" onclick="window.location.href='/product/${p.id}'">🔎 عرض التفاصيل والشراء</button>
                </div>
            </div>
        `;
    });
}

function handleSearchAndFilter() {
    const query = document.getElementById('search-box').value.toLowerCase().trim();
    const category = document.getElementById('category-filter').value;
    const sort = document.getElementById('sort-select') ? document.getElementById('sort-select').value : 'default';

    let filtered = allProducts.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(query) || (p.description && p.description.toLowerCase().includes(query));
        const matchesCategory = (category === 'all' || p.category === category);
        return matchesSearch && matchesCategory;
    });

    if (sort === 'price-low') {
        filtered.sort((a, b) => (a.selling_price || 0) - (b.selling_price || 0));
    } else if (sort === 'price-high') {
        filtered.sort((a, b) => (b.selling_price || 0) - (a.selling_price || 0));
    }

    renderProducts(filtered);
}

function updateCartUI() {
    const countEl = document.getElementById('cart-count');
    if(countEl) countEl.innerText = cart.reduce((sum, item) => sum + item.qty, 0);
}

// 🚀 دالة تتبع الشحنات الاحترافية المصلحة والمحمية من الـ Crash تماماً بنسبة 100%
async function trackMyOrder() {
    const phoneInput = document.getElementById('track-phone').value.trim();
    const out = document.getElementById('track-output');
    if(!phoneInput) { alert("من فضلك أدخل رقم الهاتف المسجل به الطلب"); return; }
    
    out.innerHTML = "🔍 جاري البحث في السجلات...";
    try {
        const res = await fetch('/api/orders');
        const orders = await res.json();
        
        // 🔒 الإصلاح السحري: تم إضافة شرط التأكد من وجود التليفون أولاً لمنع الخطأ الظاهر في السكرين شوت
        let myOrder = orders.find(o => o.customer_phone && o.customer_phone.trim() === phoneInput);
        
        if(myOrder) {
            let displayTotal = myOrder.total_price ? myOrder.total_price : (myOrder.total_val ? myOrder.total_val : 0);
            
            out.innerHTML = `
                <div style="background:#141414; padding:15px; border-radius:8px; border-right:4px solid var(--primary); margin-top:10px; text-align:right;">
                    <p style="margin:5px 0;">📦 رقم الشحنة: <strong>#${myOrder.id}</strong></p>
                    <p style="margin:5px 0;">🚦 حالة الطلب: <span style="color:var(--primary); font-weight:bold;">🔄 ${myOrder.status || 'قيد المراجعة'}</span></p>
                    <p style="margin:5px 0;">💰 إجمالي الحساب: <strong>${displayTotal} ج.م</strong></p>
                </div>
            `;
        } else {
            out.innerHTML = `<p style="color:#ef4444; text-align:center; font-weight:bold; margin-top:10px;">❌ لم نجد أي طلبات شحن مسجلة بهذا الرقم.</p>`;
        }
    } catch(e) {
        console.error(e);
        out.innerHTML = `<p style="color:#ef4444; text-align:center; margin-top:10px;">❌ حدث خطأ أثناء الاتصال بالسيرفر.</p>`;
    }
}
