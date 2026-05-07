from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "ashim_restaurant_2024"

def get_db():
    conn = sqlite3.connect("restaurant.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC")
    orders = cursor.fetchall()
  
    cursor.execute("SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = DATE('now')")
    today_orders = cursor.fetchone()["count"]
    cursor.execute("""
        SELECT SUM(menu.price * order_items.quantity) as revenue
        FROM order_items
        JOIN menu ON order_items.menu_id = menu.id
        JOIN orders ON order_items.order_id = orders.id
        WHERE orders.status = 'completed'
    """)
    result = cursor.fetchone()
    revenue = result["revenue"] if result["revenue"] else 0
    conn.close()
    return render_template("home.html", orders=orders, today_orders=today_orders, revenue=revenue)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid username or password!")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        cursor = conn.cursor()
        try:
            hashed = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except:
            conn.close()
            return render_template("register.html", error="Username already exists!")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/menu")
def menu():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu")
    items = cursor.fetchall()
    conn.close()
    return render_template("menu.html", items=items)

@app.route("/menu/add", methods=["GET", "POST"])
def add_menu():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        category = request.form["category"]
        if not name or not price:
            return render_template("add_menu.html", error="All fields are required!")
        if float(price) <= 0:
            return render_template("add_menu.html", error="Price must be greater than 0!")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO menu (name, price, category) VALUES (?, ?, ?)",
                      (name, float(price), category))
        conn.commit()
        conn.close()
        return redirect(url_for("menu"))
    return render_template("add_menu.html")

@app.route("/menu/delete/<int:id>", methods=["POST"])
def delete_menu(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("menu"))

@app.route("/order/new", methods=["GET", "POST"])
def new_order():
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cursor = conn.cursor()
    if request.method == "POST":
        table_number = request.form["table_number"]
        cursor.execute("INSERT INTO orders (table_number) VALUES (?)", (table_number,))
        order_id = cursor.lastrowid
        menu_ids = request.form.getlist("menu_id")
        quantities = request.form.getlist("quantity")
        for menu_id, quantity in zip(menu_ids, quantities):
            if int(quantity) > 0:
                cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                              (order_id, int(menu_id), int(quantity)))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))
    cursor.execute("SELECT * FROM menu")
    items = cursor.fetchall()
    conn.close()
    return render_template("new_order.html", items=items)

@app.route("/order/<int:id>")
def order_detail(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (id,))
    order = cursor.fetchone()
    cursor.execute("""
        SELECT menu.name, menu.price, order_items.quantity,
               (menu.price * order_items.quantity) as subtotal
        FROM order_items
        JOIN menu ON order_items.menu_id = menu.id
        WHERE order_items.order_id = ?
    """, (id,))
    items = cursor.fetchall()
    total = sum(item["subtotal"] for item in items)
    conn.close()
    return render_template("order_detail.html", order=order, items=items, total=total)

@app.route("/order/complete/<int:id>")
def complete_order(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'completed' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))
@app.route("/menu/edit/<int:id>")
def edit(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE id = ?", (id,))
    item = cursor.fetchone()
    conn.close()

    return render_template("edit_menu.html", item=item)
@app.route("/menu/update/<int:id>", methods=["POST"])
def update(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form["name"]
    category = request.form["category"]
    price = request.form["price"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE menu 
        SET name = ?, category = ?, price = ?
        WHERE id = ?
    """, (name, category, float(price), id))

    conn.commit()
    conn.close()

    return redirect(url_for("menu"))
@app.route("/menu/search")
def search():
    if "user_id" not in session:
        return redirect(url_for("login"))

    query = request.args.get("q")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE name LIKE ?", (f"%{query}%",))
    items = cursor.fetchall()
    conn.close()

    return render_template("menu.html", items=items, query=query)

if __name__ == "__main__":
    app.run(debug=True)