import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'gyanpustak-secret-key')

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME")
        )
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().cursor(dictionary=True)
    cur.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_type' not in session or session['user_type'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@app.route('/')
def home():
    books = query_db("SELECT b.*, COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.Review_id) as review_count FROM BOOK b LEFT JOIN REVIEW r ON b.Book_id = r.Book_id GROUP BY b.Book_id ORDER BY avg_rating DESC LIMIT 8")
    return render_template('home.html', books=books)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = query_db("SELECT * FROM USER WHERE Email = %s", [email], one=True)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['User_id']
            session['user_name'] = user['name']
            session['user_type'] = user['user_type']
            session['email'] = user['Email']
            flash('Logged in successfully!', 'success')
            if user['user_type'] == 'student':
                return redirect(url_for('books'))
            elif user['user_type'] == 'customer_support':
                return redirect(url_for('support_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    universities = query_db("SELECT * FROM UNIVERSITY")
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        university_id = request.form.get('university_id')
        dob = request.form.get('dob', '')
        status = request.form.get('status', 'undergraduate')
        major = request.form.get('major', '')
        year = request.form.get('year_of_study', 1)

        existing = query_db("SELECT User_id FROM USER WHERE Email = %s", [email], one=True)
        if existing:
            flash('Email already registered.', 'danger')
            return render_template('register.html', universities=universities)

        if not university_id:
            flash('University is required for student registration.', 'danger')
            return render_template('register.html', universities=universities)

        hashed = generate_password_hash(password)
        user_id = execute_db(
            "INSERT INTO USER (name, Email, password, phone, address, user_type) VALUES (%s,%s,%s,%s,%s,%s)",
            [name, email, hashed, phone, address, 'student']
        )
        execute_db(
            "INSERT INTO STUDENT (User_id, University_id, dob, status, major, year_of_study) VALUES (%s,%s,%s,%s,%s,%s)",
            [user_id, university_id, dob, status, major, year]
        )
        execute_db("INSERT INTO CART (User_id) VALUES (%s)", [user_id])

        session['user_id'] = user_id
        session['user_name'] = name
        session['user_type'] = 'student'
        session['email'] = email
        flash('Registration successful! Welcome to GyanPustak.', 'success')
        return redirect(url_for('books'))

    return render_template('register.html', universities=universities)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/books')
def books():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    book_type = request.args.get('type', '')
    book_format = request.args.get('format', '')
    purchase = request.args.get('purchase_option', '')

    query = """SELECT b.*, COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.Review_id) as review_count 
               FROM BOOK b LEFT JOIN REVIEW r ON b.Book_id = r.Book_id WHERE 1=1"""
    params = []

    if search:
        query += " AND (b.title LIKE %s OR b.authors LIKE %s OR b.keywords LIKE %s OR b.isbn LIKE %s)"
        s = f'%{search}%'
        params.extend([s, s, s, s])
    if category:
        query += " AND b.category = %s"
        params.append(category)
    if book_type:
        query += " AND b.type = %s"
        params.append(book_type)
    if book_format:
        query += " AND b.format = %s"
        params.append(book_format)
    if purchase:
        query += " AND b.purchase_option = %s"
        params.append(purchase)

    query += " GROUP BY b.Book_id ORDER BY b.title"
    books_list = query_db(query, params)
    categories = query_db("SELECT DISTINCT category FROM BOOK WHERE category IS NOT NULL ORDER BY category")
    return render_template('books.html', books=books_list, categories=categories,
                         search=search, category=category, book_type=book_type,
                         book_format=book_format, purchase_option=purchase)


@app.route('/books/<int:book_id>')
def book_detail(book_id):
    book = query_db("SELECT b.*, COALESCE(AVG(r.rating), 0) as avg_rating, COUNT(r.Review_id) as review_count FROM BOOK b LEFT JOIN REVIEW r ON b.Book_id = r.Book_id WHERE b.Book_id = %s GROUP BY b.Book_id", [book_id], one=True)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    reviews = query_db("SELECT r.*, u.name as reviewer_name FROM REVIEW r JOIN USER u ON r.User_id = u.User_id WHERE r.Book_id = %s ORDER BY r.date_posted DESC", [book_id])
    courses = query_db("SELECT c.*, d.name as dept_name FROM COURSE c JOIN USES us ON c.Course_id = us.Course_id JOIN OFFERS o ON c.Course_id = o.Course_id JOIN DEPARTMENT d ON o.Dept_id = d.Dept_id WHERE us.Book_id = %s", [book_id])
    return render_template('book_detail.html', book=book, reviews=reviews, courses=courses)


@app.route('/books/<int:book_id>/review', methods=['POST'])
@login_required
@role_required('student')
def add_review(book_id):
    rating = int(request.form['rating'])
    review_text = request.form.get('review_text', '')
    existing = query_db("SELECT Review_id FROM REVIEW WHERE User_id = %s AND Book_id = %s", [session['user_id'], book_id], one=True)
    if existing:
        flash('You have already reviewed this book.', 'warning')
    else:
        execute_db("INSERT INTO REVIEW (User_id, Book_id, rating, review_text) VALUES (%s,%s,%s,%s)",
                  [session['user_id'], book_id, rating, review_text])
        flash('Review submitted successfully!', 'success')
    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/cart')
@login_required
@role_required('student')
def cart():
    cart_data = query_db("SELECT * FROM CART WHERE User_id = %s", [session['user_id']], one=True)
    items = []
    total = 0
    if cart_data:
        items = query_db("""SELECT b.*, cb.quantity, (b.price * cb.quantity) as subtotal 
                           FROM CART_BOOK cb JOIN BOOK b ON cb.Book_id = b.Book_id 
                           WHERE cb.Cart_id = %s""", [cart_data['Cart_id']])
        total = sum(item['subtotal'] for item in items)
    return render_template('cart.html', items=items, total=total, cart=cart_data)


@app.route('/cart/add/<int:book_id>', methods=['POST'])
@login_required
@role_required('student')
def add_to_cart(book_id):
    cart_data = query_db("SELECT * FROM CART WHERE User_id = %s", [session['user_id']], one=True)
    if not cart_data:
        cart_id = execute_db("INSERT INTO CART (User_id) VALUES (%s)", [session['user_id']])
    else:
        cart_id = cart_data['Cart_id']

    existing = query_db("SELECT * FROM CART_BOOK WHERE Cart_id = %s AND Book_id = %s", [cart_id, book_id], one=True)
    if existing:
        execute_db("UPDATE CART_BOOK SET quantity = quantity + 1 WHERE Cart_id = %s AND Book_id = %s", [cart_id, book_id])
    else:
        execute_db("INSERT INTO CART_BOOK (Cart_id, Book_id, quantity) VALUES (%s,%s,1)", [cart_id, book_id])

    execute_db("UPDATE CART SET date_updated = %s WHERE Cart_id = %s", [datetime.now().isoformat(), cart_id])
    flash('Book added to cart!', 'success')
    return redirect(request.referrer or url_for('books'))


@app.route('/cart/remove/<int:book_id>', methods=['POST'])
@login_required
@role_required('student')
def remove_from_cart(book_id):
    cart_data = query_db("SELECT * FROM CART WHERE User_id = %s", [session['user_id']], one=True)
    if cart_data:
        execute_db("DELETE FROM CART_BOOK WHERE Cart_id = %s AND Book_id = %s", [cart_data['Cart_id'], book_id])
        execute_db("UPDATE CART SET date_updated = %s WHERE Cart_id = %s", [datetime.now().isoformat(), cart_data['Cart_id']])
    flash('Book removed from cart.', 'info')
    return redirect(url_for('cart'))


@app.route('/cart/checkout', methods=['POST'])
@login_required
@role_required('student')
def checkout():
    cart_data = query_db("SELECT * FROM CART WHERE User_id = %s", [session['user_id']], one=True)
    if not cart_data:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    items = query_db("SELECT b.*, cb.quantity FROM CART_BOOK cb JOIN BOOK b ON cb.Book_id = b.Book_id WHERE cb.Cart_id = %s", [cart_data['Cart_id']])
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    shipping = request.form.get('shipping_type', 'standard')
    cc_number = request.form.get('cc_number', '')
    cc_expiry = request.form.get('cc_expiry', '')
    cc_holder = request.form.get('cc_holder', '')
    cc_type = request.form.get('cc_type', '')

    order_id = execute_db(
        'INSERT INTO ORDERS (User_id, shipping_type, cc_number, cc_expiry, cc_holder, cc_type, status) VALUES (%s,%s,%s,%s,%s,%s,%s)',
        [session['user_id'], shipping, cc_number, cc_expiry, cc_holder, cc_type, 'new']
    )

    for item in items:
        execute_db("INSERT INTO ORDER_BOOK (Order_id, Book_id, quantity, price) VALUES (%s,%s,%s,%s)",
                  [order_id, item['Book_id'], item['quantity'], item['price']])
        execute_db("UPDATE BOOK SET quantity = GREATEST(0, quantity - %s) WHERE Book_id = %s",
                  [item['quantity'], item['Book_id']])

    execute_db("DELETE FROM CART_BOOK WHERE Cart_id = %s", [cart_data['Cart_id']])
    flash('Order placed successfully!', 'success')
    return redirect(url_for('orders'))


@app.route('/orders')
@login_required
@role_required('student')
def orders():
    order_list = query_db("""SELECT o.*, COUNT(ob.Book_id) as item_count, 
                            SUM(ob.price * ob.quantity) as total
                            FROM ORDERS o 
                            LEFT JOIN ORDER_BOOK ob ON o.Order_id = ob.Order_id 
                            WHERE o.User_id = %s 
                            GROUP BY o.Order_id ORDER BY o.date_created DESC""", [session['user_id']])
    return render_template('orders.html', orders=order_list)


@app.route('/orders/<int:order_id>')
@login_required
@role_required('student')
def order_detail(order_id):
    order = query_db('SELECT * FROM ORDERS WHERE Order_id = %s AND User_id = %s', [order_id, session['user_id']], one=True)
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('orders'))
    items = query_db("SELECT ob.*, b.title, b.authors FROM ORDER_BOOK ob JOIN BOOK b ON ob.Book_id = b.Book_id WHERE ob.Order_id = %s", [order_id])
    total = sum(i['price'] * i['quantity'] for i in items)
    return render_template('order_detail.html', order=order, items=items, total=total)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@role_required('student')
def cancel_order(order_id):
    order = query_db('SELECT * FROM ORDERS WHERE Order_id = %s AND User_id = %s', [order_id, session['user_id']], one=True)
    if order and order['status'] not in ('shipped', 'canceled'):
        execute_db('UPDATE ORDERS SET status = %s WHERE Order_id = %s', ['canceled', order_id])
        items = query_db("SELECT * FROM ORDER_BOOK WHERE Order_id = %s", [order_id])
        for item in items:
            execute_db("UPDATE BOOK SET quantity = quantity + %s WHERE Book_id = %s", [item['quantity'], item['Book_id']])
        flash('Order canceled successfully.', 'success')
    else:
        flash('This order cannot be canceled.', 'danger')
    return redirect(url_for('orders'))


@app.route('/tickets')
@login_required
@role_required('student')
def student_tickets():
    tickets = query_db("""SELECT t.*, tc.name as category_name 
                         FROM TICKET t JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
                         WHERE t.created_by = %s ORDER BY t.date_logged DESC""", [session['user_id']])
    categories = query_db("SELECT * FROM TICKET_CATEGORY")
    return render_template('tickets.html', tickets=tickets, categories=categories)


@app.route('/tickets/create', methods=['POST'])
@login_required
@role_required('student')
def create_ticket():
    title = request.form['title']
    description = request.form['description']
    category_id = request.form['category_id']

    ticket_id = execute_db(
        "INSERT INTO TICKET (title, description, status, Category_id, created_by) VALUES (%s,%s,%s,%s,%s)",
        [title, description, 'new', category_id, session['user_id']]
    )
    execute_db(
        "INSERT INTO TICKET_STATUS_LOG (new_status, Ticket_id, changed_by) VALUES (%s,%s,%s)",
        ['new', ticket_id, session['user_id']]
    )
    flash('Ticket created successfully!', 'success')
    return redirect(url_for('student_tickets'))


@app.route('/profile')
@login_required
def profile():
    user = query_db("SELECT * FROM USER WHERE User_id = %s", [session['user_id']], one=True)
    extra = None
    if session['user_type'] == 'student':
        extra = query_db("""SELECT s.*, u.name as university_name
                            FROM STUDENT s
                            JOIN UNIVERSITY u ON s.University_id = u.University_id
                            WHERE s.User_id = %s""", [session['user_id']], one=True)
    elif session['user_type'] in ('customer_support', 'admin', 'super_admin'):
        extra = query_db("SELECT * FROM EMPLOYEE WHERE User_id = %s", [session['user_id']], one=True)
    return render_template('profile.html', user=user, extra=extra)


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '')
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    execute_db("UPDATE USER SET name = %s, phone = %s, address = %s WHERE User_id = %s",
              [name, phone, address, session['user_id']])
    session['user_name'] = name

    if session['user_type'] == 'student':
        major = request.form.get('major', '')
        year = request.form.get('year_of_study', 1)
        status = request.form.get('status', 'undergraduate')
        execute_db("UPDATE STUDENT SET major = %s, year_of_study = %s, status = %s WHERE User_id = %s",
                  [major, year, status, session['user_id']])

    flash('Profile updated successfully!', 'success')
    return redirect(url_for('profile'))


@app.route('/support')
@login_required
@role_required('customer_support')
def support_dashboard():
    new_count = query_db("SELECT COUNT(*) as c FROM TICKET WHERE status = 'new'", one=True)['c']
    assigned_count = query_db("SELECT COUNT(*) as c FROM TICKET WHERE status = 'assigned'", one=True)['c']
    total_count = query_db("SELECT COUNT(*) as c FROM TICKET", one=True)['c']
    recent_tickets = query_db("""SELECT t.*, tc.name as category_name, u.name as creator_name 
                                FROM TICKET t 
                                JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
                                JOIN USER u ON t.created_by = u.User_id 
                                ORDER BY t.date_logged DESC LIMIT 10""")
    return render_template('support_dashboard.html', new_count=new_count, assigned_count=assigned_count,
                         total_count=total_count, recent_tickets=recent_tickets)


@app.route('/support/tickets')
@login_required
@role_required('customer_support')
def support_tickets():
    status_filter = request.args.get('status', '')
    query = """SELECT t.*, tc.name as category_name, u.name as creator_name 
              FROM TICKET t 
              JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
              JOIN USER u ON t.created_by = u.User_id"""
    params = []
    if status_filter:
        query += " WHERE t.status = %s"
        params.append(status_filter)
    query += " ORDER BY t.date_logged DESC"
    tickets = query_db(query, params)
    admins = query_db("SELECT u.User_id, u.name FROM USER u JOIN ADMIN a ON u.User_id = a.User_id")
    return render_template('support_tickets.html', tickets=tickets, admins=admins, status_filter=status_filter)


@app.route('/support/tickets/<int:ticket_id>/assign', methods=['POST'])
@login_required
@role_required('customer_support')
def assign_ticket(ticket_id):
    ticket = query_db("SELECT * FROM TICKET WHERE Ticket_id = %s", [ticket_id], one=True)
    if ticket and ticket['status'] == 'new':
        admin_id = request.form['admin_id']
        execute_db("UPDATE TICKET SET status = 'assigned', assigned_to = %s WHERE Ticket_id = %s", [admin_id, ticket_id])
        execute_db("INSERT INTO TICKET_STATUS_LOG (new_status, Ticket_id, changed_by) VALUES (%s,%s,%s)",
                  ['assigned', ticket_id, session['user_id']])
        flash('Ticket assigned successfully!', 'success')
    else:
        flash('Only tickets with status "new" can be assigned.', 'warning')
    return redirect(url_for('support_tickets'))


@app.route('/support/tickets/create', methods=['POST'])
@login_required
@role_required('customer_support')
def support_create_ticket():
    title = request.form['title']
    description = request.form['description']
    category_id = request.form['category_id']
    ticket_id = execute_db(
        "INSERT INTO TICKET (title, description, status, Category_id, created_by) VALUES (%s,%s,%s,%s,%s)",
        [title, description, 'new', category_id, session['user_id']]
    )
    execute_db("INSERT INTO TICKET_STATUS_LOG (new_status, Ticket_id, changed_by) VALUES (%s,%s,%s)",
              ['new', ticket_id, session['user_id']])
    flash('Ticket created successfully!', 'success')
    return redirect(url_for('support_tickets'))

@app.route('/admin')
@login_required
@role_required('admin', 'super_admin')
def admin_dashboard():
    book_count = query_db("SELECT COUNT(*) as c FROM BOOK", one=True)['c']
    student_count = query_db("SELECT COUNT(*) as c FROM STUDENT", one=True)['c']
    order_count = query_db("SELECT COUNT(*) as c FROM ORDERS", one=True)['c']
    ticket_count = query_db("SELECT COUNT(*) as c FROM TICKET WHERE status IN ('assigned','in-process')", one=True)['c']
    recent_orders = query_db("""SELECT o.*, u.name as student_name, 
                               SUM(ob.price * ob.quantity) as total
                               FROM ORDERS o 
                               JOIN USER u ON o.User_id = u.User_id 
                               LEFT JOIN ORDER_BOOK ob ON o.Order_id = ob.Order_id
                               GROUP BY o.Order_id ORDER BY o.date_created DESC LIMIT 5""")
    return render_template('admin_dashboard.html', book_count=book_count, student_count=student_count,
                         order_count=order_count, ticket_count=ticket_count, recent_orders=recent_orders)


@app.route('/admin/books')
@login_required
@role_required('admin', 'super_admin')
def admin_books():
    books_list = query_db("SELECT * FROM BOOK ORDER BY title")
    return render_template('admin_books.html', books=books_list)


@app.route('/admin/books/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_add_book():
    if request.method == 'POST':
        execute_db(
            "INSERT INTO BOOK (title, price, isbn, publisher, pub_date, edition, language, format, type, purchase_option, quantity, category, subcategory, authors, keywords) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            [request.form['title'], float(request.form['price']), request.form.get('isbn',''),
             request.form.get('publisher',''), request.form.get('pub_date',''), int(request.form.get('edition',1)),
             request.form.get('language','English'), request.form.get('format','hardcover'),
             request.form.get('type','new'), request.form.get('purchase_option','buy'),
             int(request.form.get('quantity',0)), request.form.get('category',''),
             request.form.get('subcategory',''), request.form.get('authors',''), request.form.get('keywords','')]
        )
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('admin_add_book.html')


@app.route('/admin/books/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_edit_book(book_id):
    book = query_db("SELECT * FROM BOOK WHERE Book_id = %s", [book_id], one=True)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('admin_books'))
    if request.method == 'POST':
        execute_db(
            "UPDATE BOOK SET title=%s, price=%s, isbn=%s, publisher=%s, pub_date=%s, edition=%s, language=%s, format=%s, type=%s, purchase_option=%s, quantity=%s, category=%s, subcategory=%s, authors=%s, keywords=%s WHERE Book_id=%s",
            [request.form['title'], float(request.form['price']), request.form.get('isbn',''),
             request.form.get('publisher',''), request.form.get('pub_date',''), int(request.form.get('edition',1)),
             request.form.get('language','English'), request.form.get('format','hardcover'),
             request.form.get('type','new'), request.form.get('purchase_option','buy'),
             int(request.form.get('quantity',0)), request.form.get('category',''),
             request.form.get('subcategory',''), request.form.get('authors',''), request.form.get('keywords',''), book_id]
        )
        flash('Book updated successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('admin_edit_book.html', book=book)


@app.route('/admin/books/<int:book_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_delete_book(book_id):
    execute_db("DELETE FROM REVIEW WHERE Book_id = %s", [book_id])
    execute_db("DELETE FROM CART_BOOK WHERE Book_id = %s", [book_id])
    execute_db("DELETE FROM ORDER_BOOK WHERE Book_id = %s", [book_id])
    execute_db("DELETE FROM USES WHERE Book_id = %s", [book_id])
    execute_db("DELETE FROM BOOK WHERE Book_id = %s", [book_id])
    flash('Book deleted successfully!', 'success')
    return redirect(url_for('admin_books'))


@app.route('/admin/tickets')
@login_required
@role_required('admin', 'super_admin')
def admin_tickets():
    status_filter = request.args.get('status', '')

    query = """SELECT t.*, tc.name as category_name, u.name as creator_name, 
              a.name as admin_name
              FROM TICKET t 
              JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
              JOIN USER u ON t.created_by = u.User_id 
              LEFT JOIN USER a ON t.assigned_to = a.User_id
              WHERE t.assigned_to = %s AND t.status IN ('assigned','in-process','completed')"""
    
    params = [session['user_id']]

    if status_filter:
        query = """SELECT t.*, tc.name as category_name, u.name as creator_name, 
                  a.name as admin_name
                  FROM TICKET t 
                  JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
                  JOIN USER u ON t.created_by = u.User_id 
                  LEFT JOIN USER a ON t.assigned_to = a.User_id
                  WHERE t.assigned_to = %s AND t.status = %s"""
        
        params = [session['user_id'], status_filter]

    query += " ORDER BY t.date_logged DESC"

    tickets = query_db(query, params)

    return render_template('admin_tickets.html', tickets=tickets, status_filter=status_filter)


@app.route('/admin/tickets/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_ticket_detail(ticket_id):
    ticket = query_db("""SELECT t.*, tc.name as category_name, u.name as creator_name 
                        FROM TICKET t 
                        JOIN TICKET_CATEGORY tc ON t.Category_id = tc.Category_id 
                        JOIN USER u ON t.created_by = u.User_id 
                        WHERE t.Ticket_id = %s""", [ticket_id], one=True)
    if not ticket:
        flash('Ticket not found.', 'danger')
        return redirect(url_for('admin_tickets'))

    if request.method == 'POST':
        new_status = request.form.get('status', '')
        solution = request.form.get('solution', '')
        if ticket['status'] == 'new':
            flash('Admins cannot modify tickets in "new" status.', 'warning')
        else:
            updates = []
            params = []
            if new_status and new_status != ticket['status']:
                updates.append("status = %s")
                params.append(new_status)
            if solution:
                updates.append("solution = %s")
                params.append(solution)
            if new_status == 'completed':
                updates.append("completion_date = %s")
                params.append(datetime.now().isoformat())
            if updates:
                params.append(ticket_id)
                execute_db(f"UPDATE TICKET SET {', '.join(updates)} WHERE Ticket_id = %s", params)
                if new_status and new_status != ticket['status']:
                    execute_db("INSERT INTO TICKET_STATUS_LOG (new_status, Ticket_id, changed_by) VALUES (%s,%s,%s)",
                              [new_status, ticket_id, session['user_id']])
                flash('Ticket updated successfully!', 'success')
        return redirect(url_for('admin_ticket_detail', ticket_id=ticket_id))

    logs = query_db("""SELECT tsl.*, u.name as changed_by_name 
                      FROM TICKET_STATUS_LOG tsl 
                      JOIN USER u ON tsl.changed_by = u.User_id 
                      WHERE tsl.Ticket_id = %s ORDER BY tsl.change_time""", [ticket_id])
    return render_template('admin_ticket_detail.html', ticket=ticket, logs=logs)


@app.route('/admin/orders')
@login_required
@role_required('admin', 'super_admin')
def admin_orders():
    order_list = query_db("""SELECT o.*, u.name as student_name, 
                            COUNT(ob.Book_id) as item_count, 
                            SUM(ob.price * ob.quantity) as total
                            FROM ORDERS o 
                            JOIN USER u ON o.User_id = u.User_id 
                            LEFT JOIN ORDER_BOOK ob ON o.Order_id = ob.Order_id 
                            GROUP BY o.Order_id ORDER BY o.date_created DESC""")
    return render_template('admin_orders.html', orders=order_list)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_update_order(order_id):
    new_status = request.form['status']
    execute_db('UPDATE ORDERS SET status = %s WHERE Order_id = %s', [new_status, order_id])
    if new_status == 'shipped':
        execute_db('UPDATE ORDERS SET date_fulfilled = %s WHERE Order_id = %s', [datetime.now().isoformat(), order_id])
    flash('Order status updated.', 'success')
    return redirect(url_for('admin_orders'))


@app.route('/admin/universities')
@login_required
@role_required('admin', 'super_admin')
def admin_universities():
    unis = query_db("""SELECT u.*, COUNT(DISTINCT d.Dept_id) as dept_count 
                      FROM UNIVERSITY u LEFT JOIN DEPARTMENT d ON u.University_id = d.University_id 
                      GROUP BY u.University_id""")
    return render_template('admin_universities.html', universities=unis)


@app.route('/admin/universities/add', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_add_university():
    execute_db("INSERT INTO UNIVERSITY (name, address, rep_first_name, rep_last_name, rep_email, rep_phone) VALUES (%s,%s,%s,%s,%s,%s)",
              [request.form['name'], request.form.get('address',''), request.form.get('rep_first_name',''),
               request.form.get('rep_last_name',''), request.form.get('rep_email',''), request.form.get('rep_phone','')])
    flash('University added!', 'success')
    return redirect(url_for('admin_universities'))


@app.route('/admin/departments/add', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_add_department():
    name = request.form['name'].strip()
    university_id = request.form['university_id']

    existing = query_db("SELECT Dept_id FROM DEPARTMENT WHERE name = %s AND University_id = %s",
                       [name, university_id], one=True)
    if existing:
        flash('This department already exists for the selected university.', 'warning')
    else:
        execute_db("INSERT INTO DEPARTMENT (name, University_id) VALUES (%s,%s)",
                  [name, university_id])
        flash('Department added successfully!', 'success')

    return redirect(url_for('admin_universities'))


@app.route('/admin/courses')
@login_required
@role_required('admin', 'super_admin')
def admin_courses():
    courses_list = query_db("""SELECT c.*, GROUP_CONCAT(DISTINCT d.name) as departments, 
                              GROUP_CONCAT(DISTINCT i.name) as instructors
                              FROM COURSE c 
                              LEFT JOIN OFFERS o ON c.Course_id = o.Course_id 
                              LEFT JOIN DEPARTMENT d ON o.Dept_id = d.Dept_id 
                              LEFT JOIN TEACHES t ON c.Course_id = t.Course_id 
                              LEFT JOIN INSTRUCTOR i ON t.Instructor_id = i.Instructor_id
                              GROUP BY c.Course_id ORDER BY c.name""")
    departments = query_db("SELECT * FROM DEPARTMENT ORDER BY name")
    instructors = query_db("SELECT * FROM INSTRUCTOR ORDER BY name")
    books_list = query_db("SELECT Book_id, title FROM BOOK ORDER BY title")
    return render_template('admin_courses.html', courses=courses_list, departments=departments,
                         instructors=instructors, books=books_list)


@app.route('/admin/courses/add', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_add_course():
    course_id = execute_db("INSERT INTO COURSE (name, semester, year) VALUES (%s,%s,%s)",
                          [request.form['name'], request.form.get('semester',''), int(request.form.get('year', 2025))])
    dept_id = request.form.get('dept_id')
    if dept_id:
        execute_db("INSERT INTO OFFERS (Dept_id, Course_id) VALUES (%s,%s)", [dept_id, course_id])
    instructor_id = request.form.get('instructor_id')
    if instructor_id:
        execute_db("INSERT INTO TEACHES (Instructor_id, Course_id) VALUES (%s,%s)", [instructor_id, course_id])
    book_id = request.form.get('book_id')
    if book_id:
        execute_db("INSERT INTO USES (Course_id, Book_id) VALUES (%s,%s)", [course_id, book_id])
    flash('Course added!', 'success')
    return redirect(url_for('admin_courses'))


@app.route('/admin/employees')
@login_required
@role_required('super_admin')
def admin_employees():
    employees = query_db("""SELECT u.*, e.emp_id, e.salary, e.gender, e.aadhaar,
                           CASE 
                             WHEN sa.User_id IS NOT NULL THEN 'super_admin'
                             WHEN a.User_id IS NOT NULL THEN 'admin'
                             WHEN cs.User_id IS NOT NULL THEN 'customer_support'
                           END as role
                           FROM USER u 
                           JOIN EMPLOYEE e ON u.User_id = e.User_id
                           LEFT JOIN CUSTOMER_SUPPORT cs ON u.User_id = cs.User_id
                           LEFT JOIN ADMIN a ON u.User_id = a.User_id
                           LEFT JOIN SUPER_ADMIN sa ON u.User_id = sa.User_id
                           ORDER BY u.name""")
    return render_template('admin_employees.html', employees=employees)


@app.route('/admin/employees/add', methods=['POST'])
@login_required
@role_required('super_admin')
def admin_add_employee():
    name = request.form['name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    phone = request.form.get('phone', '')
    address = request.form.get('address', '')
    emp_id = request.form['emp_id']
    salary = float(request.form.get('salary', 0))
    gender = request.form.get('gender', '')
    aadhaar = request.form.get('aadhaar', '')
    role = request.form['role']

    existing = query_db("SELECT User_id FROM USER WHERE Email = %s", [email], one=True)
    if existing:
        flash('Email already registered.', 'danger')
        return redirect(url_for('admin_employees'))

    user_id = execute_db("INSERT INTO USER (name, Email, password, phone, address, user_type) VALUES (%s,%s,%s,%s,%s,%s)",
                        [name, email, password, phone, address, role])
    execute_db("INSERT INTO EMPLOYEE (User_id, emp_id, salary, gender, aadhaar) VALUES (%s,%s,%s,%s,%s)",
              [user_id, emp_id, salary, gender, aadhaar])

    if role == 'customer_support':
        execute_db("INSERT INTO CUSTOMER_SUPPORT (User_id) VALUES (%s)", [user_id])
    elif role == 'admin':
        execute_db("INSERT INTO ADMIN (User_id) VALUES (%s)", [user_id])

    flash(f'Employee {name} added as {role}!', 'success')
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('super_admin')
def admin_delete_employee(user_id):
    # Remove role mappings first (important due to FK constraints)
    execute_db("DELETE FROM CUSTOMER_SUPPORT WHERE User_id = %s", [user_id])
    execute_db("DELETE FROM ADMIN WHERE User_id = %s", [user_id])
    execute_db("DELETE FROM SUPER_ADMIN WHERE User_id = %s", [user_id])

    # Remove employee record
    execute_db("DELETE FROM EMPLOYEE WHERE User_id = %s", [user_id])

    # Finally remove user
    execute_db("DELETE FROM USER WHERE User_id = %s", [user_id])

    flash('Employee removed successfully!', 'success')
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/<int:user_id>/salary', methods=['POST'])
@login_required
@role_required('super_admin')
def update_employee_salary(user_id):
    new_salary = request.form.get('salary')

    try:
        new_salary = float(new_salary)
    except:
        flash("Invalid salary value.", "danger")
        return redirect(url_for('admin_employees'))

    MIN_SALARY = 0
    MAX_SALARY = 200000

    if new_salary < MIN_SALARY or new_salary > MAX_SALARY:
        flash(f"Salary must be between {MIN_SALARY} and {MAX_SALARY}.", "danger")
        return redirect(url_for('admin_employees'))

    execute_db(
        "UPDATE EMPLOYEE SET salary = %s WHERE User_id = %s",
        [new_salary, user_id]
    )

    flash("Salary updated successfully!", "success")
    return redirect(url_for('admin_employees'))

@app.route('/admin/instructors')
@login_required
@role_required('admin', 'super_admin')
def admin_instructors():
    instructors = query_db("""SELECT i.*, u.name as university_name, d.name as department_name,
                              GROUP_CONCAT(DISTINCT c.name) as courses
                              FROM INSTRUCTOR i
                              LEFT JOIN UNIVERSITY u ON i.University_id = u.University_id
                              LEFT JOIN DEPARTMENT d ON i.Dept_id = d.Dept_id
                              LEFT JOIN TEACHES t ON i.Instructor_id = t.Instructor_id
                              LEFT JOIN COURSE c ON t.Course_id = c.Course_id
                              GROUP BY i.Instructor_id
                              ORDER BY i.name""")
    universities = query_db("SELECT * FROM UNIVERSITY ORDER BY name")
    departments = query_db("""SELECT d.*, u.name as university_name
                              FROM DEPARTMENT d
                              JOIN UNIVERSITY u ON d.University_id = u.University_id
                              ORDER BY u.name, d.name""")
    courses = query_db("SELECT * FROM COURSE ORDER BY name")
    return render_template('admin_instructors.html', instructors=instructors,
                         universities=universities, departments=departments, courses=courses)


@app.route('/admin/instructors/add', methods=['POST'])
@login_required
@role_required('admin', 'super_admin')
def admin_add_instructor():
    name = request.form['name']
    university_id = request.form.get('university_id') or None
    dept_id = request.form.get('dept_id') or None
    existing_course_id = request.form.get('course_id') or None
    new_course_name = request.form.get('new_course_name', '').strip()
    course_id = existing_course_id

    instructor_id = execute_db("INSERT INTO INSTRUCTOR (name, University_id, Dept_id) VALUES (%s,%s,%s)",
                              [name, university_id, dept_id])

    if course_id:
        execute_db("INSERT INTO TEACHES (Instructor_id, Course_id) VALUES (%s,%s)",
                  [instructor_id, course_id])
    else:
        if new_course_name:
            course_id = execute_db("INSERT INTO COURSE (name, semester, year) VALUES (%s,%s,%s)",
                                [new_course_name, request.form.get('new_course_semester', ''),
                                int(request.form.get('new_course_year') or 2025)])
            if dept_id:
                execute_db("INSERT INTO OFFERS (Dept_id, Course_id) VALUES (%s,%s)",
                        [dept_id, course_id])

    flash('Instructor added successfully!', 'success')
    return redirect(url_for('admin_instructors'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=False)
