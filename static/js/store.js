// ==========================================
// نظام الإشعارات الاحترافي (Toasts)
// ==========================================
function showToast(message, isError = false) {
    const container = document.getElementById('toast-container');
    if (!container) return; // إذا لم تكن الحاوية موجودة في الصفحة
    
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.backgroundColor = isError ? '#dc3545' : '#28a745';
    toast.innerText = message;
    
    container.appendChild(toast);
    
    // إظهار وإخفاء بسلاسة
    setTimeout(() => toast.classList.add('show'), 100);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==========================================
// دوال لوحة التحكم (Cashier)
// ==========================================

// 1. جلب الإحصائيات
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/stats/dashboard');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('stat-sales').innerText = `${data.total_sales} ج.م`;
            document.getElementById('stat-orders').innerText = data.total_orders;
            document.getElementById('stat-products').innerText = data.total_products;
        }
    } catch (error) {
        console.error("خطأ في جلب الإحصائيات:", error);
    }
}

// 2. جلب المنتجات للوحة الإدارة
async function loadAdminProducts() {
    try {
        const response = await fetch('/api/products');
        const products = await response.json();
        
        const tbody = document.getElementById('admin-products-list');
        tbody.innerHTML = ''; // مسح القائمة الحالية

        if (products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">لا توجد أجهزة مضافة حتى الآن.</td></tr>';
            return;
        }

        products.forEach(prod => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${prod.name}</strong></td>
                <td>${prod.category || '-'}</td>
                <td>${prod.selling_price} ج.م</td>
                <td>${prod.stock_quantity}</td>
                <td>
                    <button onclick="deleteProduct(${prod.id})" class="btn-danger">حذف</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error("خطأ:", error);
    }
}

// 3. إضافة منتج جديد
async function submitNewProduct(event) {
    event.preventDefault(); // منع إعادة تحميل الصفحة
    
    const productData = {
        name: document.getElementById('prod-name').value,
        category: document.getElementById('prod-category').value,
        buying_price: document.getElementById('prod-buy-price').value || 0,
        selling_price: document.getElementById('prod-sell-price').value,
        stock_quantity: document.getElementById('prod-stock').value || 1,
        image_url: document.getElementById('prod-image').value,
        description: document.getElementById('prod-desc').value
    };

    try {
        const response = await fetch('/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(productData)
        });

        const result = await response.json();
        
        if (response.ok && result.success) {
            showToast("✅ تم إضافة الجهاز بنجاح!");
            document.getElementById('addProductForm').reset(); // تفريغ الحقول
            loadAdminProducts(); // تحديث الجدول
            loadDashboardStats(); // تحديث الإحصائيات
        } else {
            showToast("❌ حدث خطأ أثناء الإضافة", true);
        }
    } catch (error) {
        console.error("خطأ:", error);
        showToast("❌ خطأ في الاتصال بالخادم", true);
    }
}

// 4. حذف منتج
async function deleteProduct(id) {
    if (!confirm("هل أنت متأكد من حذف هذا الجهاز بشكل نهائي؟")) return;

    try {
        const response = await fetch(`/api/products/${id}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok && result.success) {
            showToast("🗑️ تم الحذف بنجاح");
            loadAdminProducts();
            loadDashboardStats();
        } else {
            showToast("❌ فشل الحذف", true);
        }
    } catch (error) {
        console.error("خطأ:", error);
    }
}

// ==========================================
// دوال المصادقة (Auth)
// ==========================================

async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/check');
        const data = await response.json();
        
        // إذا كنا في صفحة لوحة التحكم ولم يكن مسجلاً، اطرده لصفحة الدخول
        if (!data.authenticated && window.location.pathname.includes('cashier.html')) {
            window.location.href = '/login.html';
        }
    } catch (error) {
        console.error("Auth check failed:", error);
    }
}

async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login.html';
}
