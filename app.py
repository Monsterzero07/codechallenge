from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests
from datetime import datetime
from flask import render_template

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    sold = db.Column(db.Boolean, nullable=False)
    date_of_sale = db.Column(db.String(50), nullable=False)

@app.route('/initialize', methods=['GET'])
def initialize_database():
    response = requests.get('https://s3.amazonaws.com/roxiler.com/product_transaction.json')
    
    if response.status_code == 200:
        data = response.json()
        for item in data:
            product = Product(
                id=item['id'],
                title=item['title'],
                price=item['price'],
                description=item['description'],
                category=item['category'],
                image=item['image'],
                sold=item['sold'],
                date_of_sale=item['dateOfSale']
            )
            db.session.add(product)
        db.session.commit()
        return jsonify({"message": "Database initialized successfully!"}), 201
    else:
        return jsonify({"error": "Failed to fetch data from API"}), 500
    


@app.route('/index')
def index():
    return render_template('index.html')  # Ensure index.html is in the templates folder

@app.route('/transactions', methods=['GET'])
def list_transactions():
    # Get query parameters
    month = request.args.get('month')
    search_query = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    # Filter by month if provided
    query = Product.query
    if month:
        month_number = datetime.strptime(month, '%B').month  # Convert month name to number
        query = query.filter(db.func.strftime('%m', Product.date_of_sale) == f'{month_number:02}')

    # Search filter
    if search_query:
        search_query_lower = search_query.lower()
        query = query.filter(
            (Product.title.ilike(f'%{search_query_lower}%')) |
            (Product.description.ilike(f'%{search_query_lower}%')) |
            (Product.price.like(f'%{search_query_lower}%'))
        )

    # Pagination - Corrected usage
    transactions_paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    # Prepare response data
    transactions_data = [{
        'id': product.id,
        'title': product.title,
        'price': product.price,
        'description': product.description,
        'category': product.category,
        'image': product.image,
        'sold': product.sold,
        'date_of_sale': product.date_of_sale
    } for product in transactions_paginated.items]

    return jsonify({
        'transactions': transactions_data,
        'total': transactions_paginated.total,
        'page': transactions_paginated.page,
        'per_page': transactions_paginated.per_page,
        'total_pages': transactions_paginated.pages
    }), 200

@app.route('/statistics', methods=['GET'])
def statistics():
    month = request.args.get('month')
    
    if not month:
        return jsonify({"error": "Month parameter is required"}), 400

    try:
        month_number = datetime.strptime(month, '%B').month  # Convert month name to number
        
        # Filter products by month regardless of year
        products_in_month = Product.query.filter(
            db.func.strftime('%m', Product.date_of_sale) == f'{month_number:02}'
        ).all()

        total_sales_amount = sum(product.price for product in products_in_month if product.sold)
        total_sold_items = sum(1 for product in products_in_month if product.sold)
        total_not_sold_items = sum(1 for product in products_in_month if not product.sold)

        return jsonify({
            "total_sales_amount": total_sales_amount,
            "total_sold_items": total_sold_items,
            "total_not_sold_items": total_not_sold_items
        }), 200
    
    except ValueError:
        return jsonify({"error": "Invalid month format. Please use full month names (e.g., January)."}), 400

@app.route('/bar-chart', methods=['GET'])
def bar_chart():
    month = request.args.get('month')
    
    if not month:
        return jsonify({"error": "Month parameter is required"}), 400

    try:
        month_number = datetime.strptime(month, '%B').month
        
        # Filter products by month regardless of year
        products_in_month = Product.query.filter(
            db.func.strftime('%m', Product.date_of_sale) == f'{month_number:02}'
        ).all()

        # Initialize price ranges
        price_ranges = {
            "0-100": 0,
            "101-200": 0,
            "201-300": 0,
            "301-400": 0,
            "401-500": 0,
            "501-600": 0,
            "601-700": 0,
            "701-800": 0,
            "801-900": 0,
            "901-above": 0
        }

        # Count items in each price range
        for product in products_in_month:
            price = product.price
            if price <= 100:
                price_ranges["0-100"] += 1
            elif price <= 200:
                price_ranges["101-200"] += 1
            elif price <= 300:
                price_ranges["201-300"] += 1
            elif price <= 400:
                price_ranges["301-400"] += 1
            elif price <= 500:
                price_ranges["401-500"] += 1
            elif price <= 600:
                price_ranges["501-600"] += 1
            elif price <= 700:
                price_ranges["601-700"] += 1
            elif price <= 800:
                price_ranges["701-800"] += 1
            elif price <= 900:
                price_ranges["801-900"] += 1
            else:
                price_ranges["901-above"] += 1

        return jsonify(price_ranges), 200
    
    except ValueError:
        return jsonify({"error": "Invalid month format. Please use full month names (e.g., January)."}), 400

@app.route('/pie-chart', methods=['GET'])
def pie_chart():
    month = request.args.get('month')
    
    if not month:
        return jsonify({"error": "Month parameter is required"}), 400

    try:
        month_number = datetime.strptime(month, '%B').month
        
        # Filter products by month regardless of year and group by category
        products_in_month = Product.query.filter(
            db.func.strftime('%m', Product.date_of_sale) == f'{month_number:02}'
        ).all()

        # Count items in each category
        category_counts = {}
        
        for product in products_in_month:
            category_counts[product.category] = category_counts.get(product.category, 0) + 1

        return jsonify(category_counts), 200
    
    except ValueError:
        return jsonify({"error": "Invalid month format. Please use full month names (e.g., January)."}), 400

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
