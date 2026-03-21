from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")
DATABASE = os.path.join(app.root_path, 'database.db')
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS menu (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        category TEXT,
        image TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        price REAL,
        qty INTEGER,
        note TEXT,
        status TEXT
    )''')

    conn.commit()
    conn.close()
# ================= ADMIN =================
with app.app_context():
    init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name']
        price_raw = request.form['price']
        category = request.form['category']
        image = request.files['image']

        # Buang RM jika admin key in "RM3.00"
        price_clean = price_raw.replace("RM", "").replace("rm", "").strip()

        # Pastikan harga numeric
        try:
            price = float(price_clean)
        except ValueError:
            flash("Sila masukkan harga nombor sahaja, contoh: 3.00")
            return redirect(url_for('admin'))

        # Simpan gambar jika ada
        if image.filename != '':
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
            image_name = image.filename
        else:
            image_name = ''

        # Simpan ke database
        conn.execute("INSERT INTO menu (name, price, category, image) VALUES (?, ?, ?, ?)",
                     (name, price, category, image_name))
        conn.commit()
        return redirect(url_for('admin'))

    menu = conn.execute("SELECT * FROM menu").fetchall()
    conn.close()
    return render_template('admin.html', menu=menu)


# ================= CUSTOMER =================
@app.route('/')
def index():
    conn = get_db()
    menu = conn.execute('SELECT * FROM menu').fetchall()
    conn.close()
    return render_template('index.html', menu=menu)

@app.route('/order', methods=['POST'])
def order():
    name = request.form['name']
    price = request.form['price']
    qty = int(request.form['qty'])
    note = request.form['note']

    conn = get_db()
    conn.execute('INSERT INTO orders (item_name, price, qty, note, status) VALUES (?,?,?,?,?)',
                 (name, price, qty, note, 'pending'))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

@app.route('/delete_menu/<int:id>')
def delete_menu(id):
    conn = get_db()
    conn.execute("DELETE FROM menu WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

# ================= KITCHEN =================
@app.route('/kitchen')
def kitchen():
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders WHERE status='pending'").fetchall()
    conn.close()
    return render_template('kitchen.html', orders=orders)

@app.route('/complete/<int:id>')
def complete(id):
    conn = get_db()
    conn.execute("UPDATE orders SET status='done' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('kitchen'))

@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('kitchen'))

# ================= PAYMENT =================
@app.route('/payment')
def payment():
    conn = get_db()
    orders_raw = conn.execute("SELECT * FROM orders WHERE status='done' ORDER BY id").fetchall()
    conn.close()

    orders = []
    total = 0.0
    for o in orders_raw:
        # Buang RM prefix jika ada
        price_str = str(o['price']).replace("RM", "").replace("rm", "").strip()
        try:
            price = float(price_str)
        except ValueError:
            price = 0.0  # kalau value masih error, anggap 0
        qty = int(o['qty'])
        subtotal = price * qty
        total += subtotal
        orders.append({
            'id': o['id'],
            'item_name': o['item_name'],
            'qty': qty,
            'price': price,
            'subtotal': subtotal
        })

    total = round(total, 2)

    return render_template('payment.html', orders=orders, total=total)

@app.route('/clear')
def clear():
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE status='done'")
    conn.commit()
    conn.close()
    return redirect(url_for('payment'))

# ================= RUN =================
if __name__ == '__main__':
    
    port = int(os.environ.get("PORT", 5000))  # default 5000 untuk local testing
    app.run(host="0.0.0.0", port=port, debug=True)