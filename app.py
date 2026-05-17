from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

# مصفوفة المنتجات السحابية الافتراضية
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

# مخزن الطلبات السحابية لصفحة الكاشير
cloud_orders = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cashier.html')
def cashier():
    return render_template('cashier.html')

@app.route('/marketers.html')
def marketers():
    return render_template('marketers.html')

# روابط الـ API الخاصة بالمتجر
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(cloud_products), 200

@app.route('/api/admin/orders', methods=['GET'])
def get_admin_orders():
    return jsonify(cloud_orders), 200

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    cloud_orders.append(data)
    return jsonify({"status": "success", "message": "تم تسجيل الطلب في السحابة بنجاح"}), 200

# تم تعديل هذا السطر خصيصاً ليتوافق مع معايير Vercel الصارمة لمنع فشل الـ Build
application = app

if __name__ == '__main__':
    app.run(debug=True)
