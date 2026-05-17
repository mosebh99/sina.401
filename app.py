from flask import Flask, jsonify, request, render_template

app = Flask(__name__, template_folder='.')

# قاعدة بيانات سحابية وهمية مؤقتة داخل السيرفر (تتحدث ديناميكياً من صفحة الكاشير)
# يمكنك ربطها بملف json أو داتابيز خارجية لاحقاً
cloud_products = [
    {
        "id": 1,
        "name": "زيت زيتون سيناوي بكر ممتاز",
        "category": "زيوت طبيعية",
        "selling_price": 250,
        "stock_quantity": 15,
        "image_url": "",
        "description": "زيت زيتون طبيعي 100% من معاصر سيناء بجودة عالية وفائقة."
    },
    {
        "id": 2,
        "name": "عشب المرمية السيناوية الجبلية",
        "category": "أعشاب طبيعية",
        "selling_price": 85,
        "stock_quantity": 30,
        "image_url": "",
        "description": "مرمية برية طبيعية مجففة ومقطوفة بعناية من جبال سيناء."
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

# رابط السحابية لجلب المنتجات للمتجر
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(cloud_products), 200

# رابط السحابية لاستقبال الطلبات الجديدة من الزبائن
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    print("🔔 طلب سحابي جديد وصل للسيستم:", data)
    return jsonify({"status": "success", "message": "تم تسجيل الطلب في السحابة بنجاح"}), 200

# لضمان تعرف Vercel على السيرفر كـ Handler رئيسي
application = app

if __name__ == '__main__':
    app.run(debug=True)
