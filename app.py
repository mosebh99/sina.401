from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

# قاعدة بيانات سحابية مؤقتة للمنتجات
cloud_products = [
    {
        "id": 1,
        "name": "زيت زيتون سيناوي بكر ممتاز",
        "category": "زيوت طبيعية",
        "selling_price": 250,
        "stock_quantity": 15,
        "image_url": "logo.png",
        "description": "زيت زيتون طبيعي 100% من معاصر سيناء بجودة عالية وفائقة."
    },
    {
        "id": 2,
        "name": "عشب المرمية السيناوية الجبلية",
        "category": "أعشاب طبيعية",
        "selling_price": 85,
        "stock_quantity": 30,
        "image_url": "logo.png",
        "description": "مرمية برية طبيعية مجففة ومقطوفة بعناية من جبال سيناء."
    }
]

# مخزن الطلبات المطور (يحتوي على حالة الشحن واسم المسوق لو وجد)
cloud_orders = [
    {
        "order_id": 101,
        "product_name": "زيت زيتون سيناوي بكر ممتاز",
        "quantity": 2,
        "total": 500,
        "customer_name": "أحمد علي",
        "customer_phone": "01012345678",
        "customer_address": "القاهرة - مدينة نصر",
        "status": "تم الطلب", # الحالات: تم الطلب، جاري الشحن، تم التوصيل، ملغي
        "marketer_id": "marketer_ahmed"
    }
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cashier.html')
def cashier():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

@app.route('/login.html')
def login_page():
    return render_template('login.html')

# روابط الـ API
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(cloud_products), 200

@app.route('/api/admin/orders', methods=['GET'])
def get_admin_orders():
    return jsonify(cloud_orders), 200

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    # إعطاء رقم تلقائي للطلب وتحديد الحالة الافتراضية
    data['order_id'] = len(cloud_orders) + 101
    data['status'] = "تم الطلب"
    cloud_orders.append(data)
    return jsonify({"status": "success", "order_id": data['order_id']}), 200

# رابط لتحديث حالة الشحن من صفحة الكاشير
@app.route('/api/admin/orders/update-status', methods=['POST'])
def update_order_status():
    data = request.get_json()
    order_id = int(data.get('order_id'))
    new_status = data.get('status')
    
    for order in cloud_orders:
        if order['order_id'] == order_id:
            order['status'] = new_status
            return jsonify({"status": "success", "message": f"تم تحديث الحالة إلى {new_status}"}), 200
            
    return jsonify({"status": "error", "message": "الطلب غير موجود"}), 404

application = app

if __name__ == '__main__':
    app.run(debug=True)
