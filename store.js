function formatPrice(price) {
    return new Intl.NumberFormat('ar-EG', {
        style: 'currency',
        currency: 'EGP',
        minimumFractionDigits: 0
    }).format(price);
}

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

function showToast(message, type = 'success', duration = 3000) {
    const existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        background: ${type === 'success' ? '#161616' : '#ef4444'};
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

function confirmAction(message) {
    return new Promise((resolve) => {
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
                background: #161616;
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
                        background: linear-gradient(135deg, #d4af37, #b8860b);
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

function safeStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch (e) {
        console.error('Storage error:', e);
        return false;
    }
}

function safeStorageRead(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
        console.error('Storage read error:', e);
        return defaultValue;
    }
}

const CartUtils = {
    getCart() {
        return safeStorageRead('sina_cart', []);
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

        safeStorage('sina_cart', cart);
        return cart;
    },

    removeItem(index) {
        const cart = this.getCart();
        cart.splice(index, 1);
        safeStorage('sina_cart', cart);
        return cart;
    },

    updateQty(index, qty) {
        const cart = this.getCart();
        if (qty <= 0) {
            return this.removeItem(index);
        }
        cart[index].qty = qty;
        safeStorage('sina_cart', cart);
        return cart;
    },

    clearCart() {
        localStorage.removeItem('sina_cart');
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

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        formatPrice,
        formatDate,
        showToast,
        confirmAction,
        safeStorage,
        safeStorageRead,
        CartUtils,
        API
    };
}
