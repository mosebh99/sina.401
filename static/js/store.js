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
        container.innerHTML += `
            <div class="product-card">
                <img src="${p.image_url || '/static/css/logo.png.jpeg'}" loading="lazy" alt="${p.name}">
                <div class="card-body">
                    <h3><a href="/product/${p.id}">${p.name}</a></h3>
                    <p style="color: var(--text-muted); font-size: 13px;">${p.description ? p.description.substring(0, 50) + '...' : 'لا يوجد وصف.'}</p>
                    <div class="price-box">${p.selling_price} ج.م</div>
                    <button class="btn-primary" onclick="addToCart(${p.id}, '${p.name}', ${p.selling_price})">🛒 إضافة للسلة</button>
                </div>
            </div>
        `;
    });
}

// محرك الفلترة والبحث المباشر
function handleSearchAndFilter() {
    const query = document.getElementById('search-box').value.toLowerCase();
    const category = document.getElementById('filter-category').value;
    const sort = document.getElementById('sort-select').value;
    
    let result = allProducts.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(query) || (p.description && p.description.toLowerCase().includes(query));
        const matchesCategory = (category === 'الكل' || p.category === category);
        return matchesSearch && matchesCategory;
    });

    if (sort === 'price-low') result.sort((a,b) => a.selling_price - b.selling_price);
    else if (sort === 'price-high') result.sort((a,b) => b.selling_price - a.selling_price);

    renderProducts(result);
}

function addToCart(id, name, price) {
    const index = cart.findIndex(item => item.id === id);
    if(index > -1) {
        cart[index].qty += 1;
    } else {
        cart.push({ id, name, price, qty: 1 });
    }
    saveCart();
    showToast(`✅ تم إضافة ${name} إلى السلة!`);
}

function saveCart() {
    localStorage.setItem('sinaa_cart', JSON.stringify(cart));
    updateCartUI();
}

function updateCartUI() {
    const countBadge = document.getElementById('cart-count');
    if(countBadge) countBadge.innerText = cart.reduce((s, i) => s + i.qty, 0);
}

// 🎯 التعديل والإصلاح الجذري لدالة تتبع الطلبات لمنع خطأ trackMyOrder نهائياً
async function trackMyOrder() {
    const phoneInput = document.getElementById('track-phone').value.trim();
    const out = document.getElementById('track-output');
    if(!phoneInput) { alert("من فضلك أدخل رقم الهاتف المسجل به الطلب"); return; }
    
    out.innerHTML = "🔍 جاري البحث في السجلات...";
    try {
        const res = await fetch('/api/public/orders');
        const orders = await res.json();
        
        let myOrder = orders.find(o => o.customer_phone.trim() === phoneInput);
        
        if(myOrder) {
            // الاستبدال المصلح لمنع توقف السكربت والـ Crash والعمل بكفاءة تامة
            let displayTotal = myOrder.total_price ? myOrder.total_price : myOrder.total;
            
            out.innerHTML = `
                <div style="background:#141414; padding:15px; border-radius:8px; border-right:4px solid var(--primary); margin-top:10px; text-align:right;">
                    <p>📦 رقم الشحنة: <strong>#${myOrder.id}</strong></p>
                    <p>🚦 حالة الطلب: <span style="color:var(--primary); font-weight:bold;">${myOrder.status}</span></p>
                    <p>💰 إجمالي الحساب: <strong>${displayTotal} ج.م</strong></p>
                </div>
            `;
        } else {
            out.innerHTML = `<span style="color:#dc2626;">❌ لم نجد أي طلبات شحن مسجلة بهذا الهاتف.</span>`;
        }
    } catch (e) {
        out.innerHTML = "❌ حدث خطأ أثناء تتبع الشحنة.";
    }
}
