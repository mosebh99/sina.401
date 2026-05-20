/**
 * Sina 401 Store - JavaScript Utilities
 * ملف مساعد للوظائف المشتركة في المتجر
 */

// ==========================================
// Utility Functions
// ==========================================

/**
 * تنسيق السعر بالعملة المصرية
 */
function formatPrice(price) {
    return new Intl.NumberFormat('ar-EG', {
        style: 'currency',
        currency: 'EGP',
        minimumFractionDigits: 0
    }).format(price);
}

/**
 * تنسيق التاريخ بالعربية
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-EG', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * إظهار إشعار Toast
 */
function showToast(message, type = 'success', duration = 3000) {
    // إزالة أي Toast موجود
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        background: ${type === 'success' ? '#141414' : '#ef4444'};
        border-right: 4px solid ${type === 'success' ? '#d4af37' : '#ef4444'};
        color: #fff;
        padding: 15px 25px;
        border-radius: 8px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.7);
        z-index: 99999;
        animation: slideIn 0.3s ease-out;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
        max-width: 300px;
        word-wrap: break-word;
    `;
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 20px;">${type === 'success' ? '✅' : '❌'}</span>
            <span>${message}</span>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * تأكيد العملية
 */
function confirmAction(message) {
    return new Promise((resolve) => {
        // إنشاء modal مخصص
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            backdrop-filter: blur(5px);
        `;

        modal.innerHTML = `
            <div style="
                background: #141414;
                border: 1px solid #333;
                border-radius: 12px;
                padding: 30px;
                max-width: 400px;
                text-align: center;
                animation: fadeIn 0.3s ease-out;
            ">
                <div style="font-size: 40px; margin-bottom: 15px;">⚠️</div>
                <h3 style="color: #fff; margin: 0 0 15px 0;">تأكيد العملية</h3>
                <p style="color: #aaa; margin-bottom: 25px;">${message}</p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="confirm-yes" style="
                        background: linear-gradient(135deg, #d4af37, #aa8416);
                        color: #000;
                        border: none;
                        padding: 10px 25px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: bold;
                        font-family: inherit;
                    ">نعم، متابعة</button>
                    <button id="confirm-no" style="
                        background: #222;
                        color: #fff;
                        border: 1px solid #333;
                        padding: 10px 25px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-family: inherit;
                    ">إلغاء</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.querySelector('#confirm-yes').onclick = () => {
            modal.remove();
            resolve(true);
        };

        modal.querySelector('#confirm-no').onclick = () => {
            modal.remove();
            resolve(false);
        };

        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
                resolve(false);
            }
        };
    });
}

/**
 * عرض Loader
 */
function showLoader(containerId, message = 'جاري التحميل...') {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div style="
                width: 40px;
                height: 40px;
                border: 3px solid #222;
                border-top-color: #d4af37;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            "></div>
            <p style="color: #aaa; font-size: 14px;">${message}</p>
        </div>
    `;
}

/**
 * إخفاء Loader
 */
function hideLoader(containerId) {
    const container = document.getElementById(containerId);
    if (container) container.innerHTML = '';
}

/**
 * التحقق من صحة رقم الهاتف المصري
 */
function validateEgyptianPhone(phone) {
    const cleaned = phone.replace(/\D/g, '');
    const regex = /^(01[0-2,5]{1}[0-9]{8})$/;
    return regex.test(cleaned);
}

/**
 * التحقق من صحة البريد الإلكتروني
 */
function validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * حفظ في LocalStorage بشكل آمن
 */
function safeStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.error('Storage error:', e);
        return false;
    }
}

/**
 * قراءة من LocalStorage بشكل آمن
 */
function safeStorageRead(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.error('Storage read error:', e);
        return defaultValue;
    }
}

/**
 * إنشاء معرف فريد
 */
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * تأخير (Debouncing)
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * تقليل (Throttling)
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==========================================
// Cart Utilities
// ==========================================

const CartUtils = {
    getCart() {
        return safeStorageRead('sina_store_cart', []);
    },

    addItem(product) {
        const cart = this.getCart();
        const existing = cart.find(item => item.id === product.id);

        if (existing) {
            existing.qty += product.qty || 1;
        } else {
            cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                qty: product.qty || 1,
                image: product.image || '/static/css/logo.png.jpeg'
            });
        }

        safeStorage('sina_store_cart', cart);
        return cart;
    },

    removeItem(index) {
        const cart = this.getCart();
        cart.splice(index, 1);
        safeStorage('sina_store_cart', cart);
        return cart;
    },

    updateQty(index, qty) {
        const cart = this.getCart();
        if (qty <= 0) {
            return this.removeItem(index);
        }
        cart[index].qty = qty;
        safeStorage('sina_store_cart', cart);
        return cart;
    },

    clearCart() {
        localStorage.removeItem('sina_store_cart');
        return [];
    },

    getTotal() {
        const cart = this.getCart();
        return cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    },

    getCount() {
        const cart = this.getCart();
        return cart.reduce((sum, item) => sum + item.qty, 0);
    }
};

// ==========================================
// API Utilities
// ==========================================

const API = {
    async get(url) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async post(url, data) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async put(url, data) {
        const res = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },

    async delete(url) {
        const res = await fetch(url, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
};

// ==========================================
// Export for modules
// ==========================================
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatPrice,
        formatDate,
        showToast,
        confirmAction,
        showLoader,
        hideLoader,
        validateEgyptianPhone,
        validateEmail,
        safeStorage,
        safeStorageRead,
        generateId,
        debounce,
        throttle,
        CartUtils,
        API
    };
}
