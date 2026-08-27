import sqlite3
from config import DB_NAME

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabel Produk (Lengkap dengan Stock & Auto Content Delivery)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            stock INTEGER DEFAULT 0,
            digital_content TEXT
        )
    ''')
    
    # Tabel Payment Methods
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            method TEXT PRIMARY KEY,
            info TEXT NOT NULL
        )
    ''')
    
    # Tabel Cart
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            PRIMARY KEY (user_id, product_id)
        )
    ''')
    
    # Tabel Transaksi / Orders
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            proof_photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabel Detail Order (Items)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            order_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            price REAL,
            quantity INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')
    
    # Tabel Pengguna Registered
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# --- HELPER PRODUK ---
def db_add_product(name, price, description, stock=999, digital_content=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, description, stock, digital_content) VALUES (?, ?, ?, ?, ?)",
        (name, price, description, stock, digital_content)
    )
    conn.commit()
    conn.close()

def db_get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()
    conn.close()
    return rows

def db_get_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def db_update_product_desc(product_id, new_desc):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET description = ? WHERE id = ?", (new_desc, product_id))
    conn.commit()
    conn.close()

def db_delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

# --- HELPER PAYMENT ---
def db_set_payment_info(method, info):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO payments (method, info) VALUES (?, ?)", (method.lower(), info))
    conn.commit()
    conn.close()

def db_get_payment_info(method):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT info FROM payments WHERE method = ?", (method.lower(),))
    row = cursor.fetchone()
    conn.close()
    return row['info'] if row else None

# --- HELPER CART ---
def db_add_to_cart(user_id, product_id, qty=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?", (qty, user_id, product_id))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, qty))
    conn.commit()
    conn.close()

def db_get_cart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.name, p.price, c.quantity, p.digital_content 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def db_clear_cart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- HELPER ORDERS & TRANSAKSI ---
def db_create_order(user_id, total_amount, cart_items):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (?, ?, 'pending')", (user_id, total_amount))
    order_id = cursor.lastrowid
    
    for item in cart_items:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (?, ?, ?, ?, ?)",
            (order_id, item['id'], item['name'], item['price'], item['quantity'])
        )
    conn.commit()
    conn.close()
    return order_id

def db_update_order_status(order_id, status, proof_photo=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if proof_photo:
        cursor.execute("UPDATE orders SET status = ?, proof_photo = ? WHERE id = ?", (status, proof_photo, order_id))
    else:
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()

def db_get_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    if order:
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        items = cursor.fetchall()
        conn.close()
        return order, items
    conn.close()
    return None, []

def db_get_user_orders(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def db_register_user(user_id, username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def db_get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM orders WHERE status = 'paid'")
    orders_data = cursor.fetchone()
    conn.close()
    return total_users, orders_data[0] or 0, orders_data[1] or 0.0
