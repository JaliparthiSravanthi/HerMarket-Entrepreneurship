from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

DATABASE = "hermarket.db"

# ================= DATABASE CONNECTION =================
def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ================= CREATE TABLES =================
def create_tables():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS entrepreneurs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        business TEXT,
        location TEXT,
        tag TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        location TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        price TEXT,
        category TEXT,
        owner TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_activity(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        category TEXT
    )
    """)

    conn.commit()
    conn.close()

create_tables()

# ================= HOME =================
@app.route("/")
def home():
    return render_template("FRONTENDher.html")

# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    role = request.form.get("role")
    if role == "seller":
        return redirect("/seller")
    elif role == "customer":
        return redirect("/customer")
    return redirect("/")

# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():
    role = request.form.get("role")
    name = request.form.get("name")
    location = request.form.get("location")
    business = request.form.get("business")

    conn = get_connection()

    if role == "seller":
        conn.execute("""
            INSERT INTO entrepreneurs (name, business, location, tag)
            VALUES (?, ?, ?, ?)
        """, (name, business, location, "Women-Owned Business"))
        conn.commit()
        conn.close()
        return redirect("/seller")

    elif role == "customer":
        conn.execute("""
            INSERT INTO customers (name, location)
            VALUES (?, ?)
        """, (name, location))
        conn.commit()
        conn.close()
        return redirect("/customer")

    return redirect("/")

# ================= AI RECOMMENDATION =================
def recommend_products(customer_id):
    conn = get_connection()
    activity = conn.execute("""
        SELECT category FROM user_activity
        WHERE customer_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (customer_id,)).fetchone()

    if not activity:
        conn.close()
        return []

    category = activity["category"]
    products = conn.execute("""
        SELECT * FROM products
        WHERE category = ?
        LIMIT 5
    """, (category,)).fetchall()

    conn.close()
    return [dict(p) for p in products]

def add_dummy_activity(customer_id):
    conn = get_connection()
    conn.execute("""
        INSERT INTO user_activity (customer_id, category)
        VALUES (?, ?)
    """, (customer_id, "Accessories"))
    conn.commit()
    conn.close()

# ================= DASHBOARDS =================
@app.route("/seller")
def seller():

    conn = get_connection()
    seller = conn.execute("SELECT * FROM entrepreneurs LIMIT 1").fetchone()
    conn.close()

    return render_template("seller_dashboard.html", seller=seller)

@app.route("/customer")
def customer():
    customer_id = 1  # demo user
    add_dummy_activity(customer_id)
    recommendations = recommend_products(customer_id)

    return render_template(
        "customer_dashboard.html",
        recommendations=recommendations
    )
@app.route("/update-profile/<old_name>", methods=["POST"])
def update_profile(old_name):

    new_name = request.form.get("name")
    business = request.form.get("business")
    location = request.form.get("location")

    conn = get_connection()

    conn.execute("""
        UPDATE entrepreneurs
        SET name = ?, business = ?, location = ?
        WHERE name = ?
    """, (new_name, business, location, old_name))

    conn.commit()
    conn.close()

    return redirect("/seller")
# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)