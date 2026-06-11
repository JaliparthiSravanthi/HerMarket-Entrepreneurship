
from flask import Flask, request, jsonify, render_template, redirect, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CORS(app)
app.secret_key = "hermarket_secret_key"

# ================= HOME =================
@app.route("/")
def home():
    return render_template("FRONTENDher.html")

# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():

    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM users WHERE email=%s AND role=%s"
    cursor.execute(query, (email, role))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user is None:
        return "Invalid email or password"

    if check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["email"] = user["email"]

        if user["role"] == "seller":
            return redirect("/seller")

        elif user["role"] == "customer":
            return redirect("/customer")

    return "Invalid email or password"

# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    print("REGISTER ROUTE HIT")
    role = request.form.get("role")
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    print(request.form)
    print(name, email, password, role)

    if password != confirm_password:
        return "Passwords do not match"

    hashed_password = generate_password_hash(password)

    try:

      conn = get_connection()
      cursor = conn.cursor()

      query = """
      INSERT INTO users(username, email, password, role)
      VALUES(%s, %s, %s, %s)
      """

      values = (name, email, hashed_password, role)

      cursor.execute(query, values)

      conn.commit()

      print("DATA INSERTED SUCCESSFULLY")

      cursor.close()
      conn.close()

    except Exception as e:
      print("DATABASE ERROR:")
      print(e)
    return "Registration Successful"

# ================= AI RECOMMENDATION =================
def recommend_products(customer_id):

    # DATABASE LOGIC WILL BE ADDED LATER
    recommendations = []

    return recommendations

# ================= DASHBOARDS =================
@app.route("/seller")
def seller():

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM products WHERE seller_id=%s"
    cursor.execute(query, (seller_id,))

    products = cursor.fetchall()

    cursor.close()
    conn.close()

    seller = {
        "name": session["email"],
        "business": "",
        "location": ""
    }

    return render_template(
        "seller_dashboard.html",
        seller=seller,
        products=products
    )

@app.route("/customer")
def customer():

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "customer":
        return redirect("/")

    category = request.args.get("category")
    search = request.args.get("search")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
    SELECT products.*,
       ROUND(AVG(reviews.rating), 1) AS avg_rating,
       COUNT(reviews.id) AS review_count
   FROM products
   LEFT JOIN reviews
   ON products.id = reviews.product_id
   WHERE 1=1
   """

    values = []

    if category:
       query += " AND products.category=%s"
       values.append(category)

    if search:
       query += """
      AND (
        products.title LIKE %s
        OR products.category LIKE %s
        OR products.description LIKE %s
        )
      """
       values.append("%" + search + "%")
       values.append("%" + search + "%")
       values.append("%" + search + "%")

    query += " GROUP BY products.id"

    cursor.execute(query, tuple(values))
    products = cursor.fetchall()

    return render_template(
        "customer_dashboard.html",
        products=products,
        selected_category=category,
        search=search
    )
# ================= UPDATE PROFILE =================
@app.route("/update-profile/<old_name>", methods=["POST"])
def update_profile(old_name):

    new_name = request.form.get("name")
    business = request.form.get("business")
    location = request.form.get("location")

    # DATABASE LOGIC WILL BE ADDED LATER
    return redirect("/seller")

@app.route("/add-product", methods=["POST"])
def add_product():

    if "user_id" not in session:
        return redirect("/")

    title = request.form.get("title")
    description = request.form.get("description")
    price = request.form.get("price")
    category = request.form.get("category")
    stock = request.form.get("stock")
    seller_id = session["user_id"]
    
    image = request.files.get("image")
    image_filename = None

    if image and image.filename != "":
        image_filename = secure_filename(image.filename)
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO products
(title, description, price, category, image, seller_id, stock)
VALUES(%s, %s, %s, %s, %s, %s, %s)
    """

    values = (title, description, price, category, image_filename, seller_id,stock)

    cursor.execute(query, values)
    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/seller")

@app.route("/product/<int:id>")
def product_details(id):

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # PRODUCT DETAILS
    query = "SELECT * FROM products WHERE id=%s"
    cursor.execute(query, (id,))

    product = cursor.fetchone()

    if product is None:
        cursor.close()
        conn.close()
        return "Product not found"

    # PRODUCT REVIEWS
    review_query = """
    SELECT reviews.*,
           users.username
    FROM reviews
    JOIN users
    ON reviews.user_id = users.id
    WHERE reviews.product_id=%s
    ORDER BY reviews.created_at DESC
    """

    cursor.execute(review_query, (id,))

    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "product_details.html",
        product=product,
        reviews=reviews
    )
@app.route("/delete-product/<int:id>")
def delete_product(id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    DELETE FROM products
    WHERE id=%s AND seller_id=%s
    """

    values = (id, session["user_id"])

    cursor.execute(query, values)

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/seller")
@app.route("/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "seller":
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":

        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price")
        category = request.form.get("category")
        stock = request.form.get("stock")
        
        query = """
UPDATE products
SET title=%s,
    description=%s,
    price=%s,
    category=%s,
    stock=%s
WHERE id=%s AND seller_id=%s
"""

        values = (
          title,
          description,
          price,
          category,
          stock,
          id,
         session["user_id"]
    )

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/seller")

    query = "SELECT * FROM products WHERE id=%s AND seller_id=%s"
    cursor.execute(query, (id, session["user_id"]))

    product = cursor.fetchone()

    cursor.close()
    conn.close()

    if product is None:
        return "Product not found"

    return render_template("edit_product.html", product=product)



@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT cart.id,
           products.title,
           products.price,
           products.image,
           cart.quantity
    FROM cart
    JOIN products
    ON cart.product_id = products.id
    WHERE cart.user_id=%s
    """

    cursor.execute(query, (user_id,))
    cart_items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "cart.html",
        cart_items=cart_items
    )
@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    DELETE FROM cart
    WHERE id=%s AND user_id=%s
    """

    cursor.execute(query, (cart_id, session["user_id"]))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/cart")
@app.route("/increase-quantity/<int:cart_id>")
def increase_quantity(cart_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE cart
    SET quantity = quantity + 1
    WHERE id=%s AND user_id=%s
    """

    cursor.execute(query, (cart_id, session["user_id"]))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/cart")
@app.route("/decrease-quantity/<int:cart_id>")
def decrease_quantity(cart_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT quantity FROM cart WHERE id=%s AND user_id=%s",
        (cart_id, session["user_id"])
    )

    item = cursor.fetchone()

    if item and item["quantity"] > 1:
        cursor.execute(
            "UPDATE cart SET quantity = quantity - 1 WHERE id=%s AND user_id=%s",
            (cart_id, session["user_id"])
        )
    else:
        cursor.execute(
            "DELETE FROM cart WHERE id=%s AND user_id=%s",
            (cart_id, session["user_id"])
        )


    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/cart") 
@app.route("/checkout")
def checkout():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT cart.*, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    cart_items = cursor.fetchall()

    total = 0
    for item in cart_items:
        total += item["price"] * item["quantity"]

    cursor.execute("""
        SELECT *
        FROM addresses
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))

    address = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "checkout.html",
        total=total,
        address=address
    )
@app.route("/place-order", methods=["POST"])
def place_order():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # GET CART ITEMS
    cursor.execute("""
        SELECT cart.product_id, cart.quantity, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    cart_items = cursor.fetchall()

    if len(cart_items) == 0:
        cursor.close()
        conn.close()
        return redirect("/cart")

    # GET LATEST ADDRESS
    cursor.execute("""
        SELECT id
        FROM addresses
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id,))

    address = cursor.fetchone()

    if address is None:
        cursor.close()
        conn.close()
        return redirect("/address")

    address_id = address["id"]

    # CALCULATE TOTAL
    total = 0
    for item in cart_items:
        total += item["price"] * item["quantity"]

    # CREATE ORDER WITH ADDRESS
    cursor.execute("""
        INSERT INTO orders(user_id, total_amount, address_id)
        VALUES(%s, %s, %s)
    """, (user_id, total, address_id))

    order_id = cursor.lastrowid

    # CREATE ORDER ITEMS
    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_items(order_id, product_id, quantity, price)
            VALUES(%s, %s, %s, %s)
        """, (
            order_id,
            item["product_id"],
            item["quantity"],
            item["price"]
        ))
    cursor.execute("""
        UPDATE products
        SET stock = stock - %s
        WHERE id = %s
    """, (
        item["quantity"],
        item["product_id"]
    ))

    # CLEAR CART
    cursor.execute(
        "DELETE FROM cart WHERE user_id=%s",
        (user_id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/my-orders")
@app.route("/my-orders")
def my_orders():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT *
    FROM orders
    WHERE user_id=%s
    ORDER BY created_at DESC
    """

    cursor.execute(query, (user_id,))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("my_orders.html", orders=orders)
@app.route("/order-details/<int:order_id>")
def order_details(order_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        orders.id AS order_id,
        orders.total_amount,
        orders.status,
        orders.created_at,
        products.id AS product_id,
        products.title,
        products.image,
        order_items.quantity,
        order_items.price
    FROM orders
    JOIN order_items
    ON orders.id = order_items.order_id
    JOIN products
    ON order_items.product_id = products.id
    WHERE orders.id=%s AND orders.user_id=%s
    """

    cursor.execute(query, (order_id, session["user_id"]))
    items = cursor.fetchall()

    if not items:
        cursor.close()
        conn.close()
        return "Order not found"

    cursor.execute("""
        SELECT product_id
        FROM reviews
        WHERE user_id=%s AND order_id=%s
    """, (session["user_id"], order_id))

    reviewed_products = cursor.fetchall()

    reviewed_product_ids = []

    for review in reviewed_products:
        reviewed_product_ids.append(review["product_id"])

    cursor.close()
    conn.close()

    return render_template(
        "order_details.html",
        items=items,
        reviewed_product_ids=reviewed_product_ids
    )
@app.route("/address", methods=["GET", "POST"])
def address():

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "customer":
        return redirect("/")

    if request.method == "POST":

        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        address = request.form.get("address")
        city = request.form.get("city")
        state = request.form.get("state")
        pincode = request.form.get("pincode")

        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO addresses
        (user_id, full_name, phone, address, city, state, pincode)
        VALUES(%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            session["user_id"],
            full_name,
            phone,
            address,
            city,
            state,
            pincode
        )

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return redirect("/checkout")

    return render_template("address.html")
@app.route("/update-order-status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "seller":
        return redirect("/")

    status = request.form.get("status")
    seller_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    UPDATE orders
    JOIN order_items ON orders.id = order_items.order_id
    JOIN products ON order_items.product_id = products.id
    SET orders.status=%s
    WHERE orders.id=%s AND products.seller_id=%s
    """

    cursor.execute(query, (status, order_id, seller_id))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/seller-orders")
@app.route("/add-review/<int:product_id>/<int:order_id>", methods=["POST"])
def add_review(product_id, order_id):

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]
    rating = request.form.get("rating")
    comment = request.form.get("comment")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM reviews
        WHERE user_id=%s AND product_id=%s AND order_id=%s
    """, (user_id, product_id, order_id))

    existing_review = cursor.fetchone()

    if existing_review:
        cursor.close()
        conn.close()
        return redirect(f"/order-details/{order_id}")

    cursor.execute("""
        INSERT INTO reviews(user_id, product_id, order_id, rating, comment)
        VALUES(%s, %s, %s, %s, %s)
    """, (
        user_id,
        product_id,
        order_id,
        rating,
        comment
    ))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(f"/order-details/{order_id}")
@app.route("/seller-analytics")
def seller_analytics():

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Total Products
    cursor.execute(
        "SELECT COUNT(*) AS total_products FROM products WHERE seller_id=%s",
        (seller_id,)
    )
    total_products = cursor.fetchone()["total_products"]

    # 2. Total Orders
    cursor.execute("""
        SELECT COUNT(DISTINCT orders.id) AS total_orders
        FROM orders
        JOIN order_items ON orders.id = order_items.order_id
        JOIN products ON order_items.product_id = products.id
        WHERE products.seller_id=%s
    """, (seller_id,))
    total_orders = cursor.fetchone()["total_orders"]

    # 3. Total Revenue
    cursor.execute("""
        SELECT SUM(order_items.price * order_items.quantity) AS total_revenue
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE products.seller_id=%s
    """, (seller_id,))
    total_revenue = cursor.fetchone()["total_revenue"]

    if total_revenue is None:
        total_revenue = 0

    # 4. Average Rating
    cursor.execute("""
        SELECT ROUND(AVG(reviews.rating), 1) AS avg_rating
        FROM reviews
        JOIN products ON reviews.product_id = products.id
        WHERE products.seller_id=%s
    """, (seller_id,))
    avg_rating = cursor.fetchone()["avg_rating"]

    if avg_rating is None:
        avg_rating = "No ratings yet"

    cursor.close()
    conn.close()

    return render_template(
        "seller_analytics.html",
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        avg_rating=avg_rating
    )
@app.route("/add-to-wishlist/<int:product_id>")
def add_to_wishlist(product_id):

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM wishlist WHERE user_id=%s AND product_id=%s",
        (user_id, product_id)
    )

    existing = cursor.fetchone()

    if existing is None:
        cursor.execute(
            "INSERT INTO wishlist(user_id, product_id) VALUES(%s, %s)",
            (user_id, product_id)
        )
        conn.commit()

    cursor.close()
    conn.close()

    return redirect("/customer")
@app.route("/wishlist")
def wishlist():

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT wishlist.id AS wishlist_id,
           products.id AS product_id,
           products.title,
           products.price,
           products.image,
           products.category
    FROM wishlist
    JOIN products
    ON wishlist.product_id = products.id
    WHERE wishlist.user_id=%s
    """

    cursor.execute(query, (user_id,))
    wishlist_items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "wishlist.html",
        wishlist_items=wishlist_items
    )
@app.route("/remove-wishlist/<int:wishlist_id>")
def remove_wishlist(wishlist_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM wishlist WHERE id=%s AND user_id=%s",
        (wishlist_id, session["user_id"])
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/wishlist")
@app.route("/seller-orders")
def seller_orders():

    if "user_id" not in session:
        return redirect("/")

    if session["role"] != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT
        orders.id AS order_id,
        orders.status,
        orders.created_at,
        users.username AS customer_name,
        products.title,
        products.image,
        order_items.quantity,
        order_items.price,
        addresses.full_name,
        addresses.phone,
        addresses.address,
        addresses.city,
        addresses.state,
        addresses.pincode
    FROM order_items
    JOIN orders
        ON order_items.order_id = orders.id
    JOIN products
        ON order_items.product_id = products.id
    JOIN users
        ON orders.user_id = users.id
    LEFT JOIN addresses
        ON orders.address_id = addresses.id
    WHERE products.seller_id = %s
    ORDER BY orders.created_at DESC
    """

    cursor.execute(query, (seller_id,))
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("seller_orders.html", orders=orders)
@app.route("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):

    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # CHECK PRODUCT STOCK
    cursor.execute(
        "SELECT stock FROM products WHERE id=%s",
        (product_id,)
    )

    product = cursor.fetchone()

    if product is None or product["stock"] <= 0:
        cursor.close()
        conn.close()
        return redirect("/customer")

    # CHECK IF PRODUCT ALREADY IN CART
    cursor.execute(
        "SELECT * FROM cart WHERE user_id=%s AND product_id=%s",
        (user_id, product_id)
    )

    item = cursor.fetchone()

    if item:

        # Do not allow cart quantity more than stock
        if item["quantity"] < product["stock"]:
            cursor.execute(
                "UPDATE cart SET quantity = quantity + 1 WHERE id=%s",
                (item["id"],)
            )

    else:
        cursor.execute(
            "INSERT INTO cart(user_id, product_id, quantity) VALUES(%s, %s, %s)",
            (user_id, product_id, 1)
        )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/customer")
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)


