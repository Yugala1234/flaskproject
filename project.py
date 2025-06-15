from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime,timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import logging
app = Flask(__name__)
app.secret_key = 'secret-key'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database1.db'

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yugalapatibandla@gmail.com'  #email
#https://myaccount.google.com/apppasswords
app.config['MAIL_PASSWORD'] = 'gfcb iege lavw quwa'  # App password
app.config['MAIL_DEFAULT_SENDER'] = 'yugalapatibandla@gmail.com'  # Default sender

mail = Mail(app)
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    role = db.Column(db.String(10))  # 'admin' or 'user'
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(100),unique=True)
    password = db.Column(db.String(200))

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150))
    author = db.Column(db.String(100))
    total_copies = db.Column(db.Integer)
    available_copies = db.Column(db.Integer)

class Borrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    borrow_date = db.Column(db.DateTime)
    user = db.relationship('User', backref='borrows')
    book = db.relationship('Book', backref='borrows')

class Waitlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    request_date = db.Column(db.DateTime, default=datetime.now)

# Authentication Decorators
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admin access only.")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/init_db')
def init_db():
    db.create_all()
    return "Database initialized!"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('register'))
        user = User(name=name, role=role, username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect(url_for('login'))
    return render_template('register1.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['role'] = user.role
            flash(f"Welcome, {user.name}!")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])

    if session['role'] == 'admin':
        members = User.query.filter_by(role='user').all()
        books = Book.query.all()
        member_count = len(members)
        book_count = len(books)
        return render_template(
            'dashboard_admin.html',
            user=user,
            members=members,
            books=books,
            member_count=member_count,
            book_count=book_count
        )
    else:
        books = Book.query.all()
        borrowed = Borrow.query.filter_by(user_id=user.id).all()
        book_count = len(books)
        return render_template(
            'dashboard_user.html',
            user=user,
            books=books,
            borrowed=borrowed,
            book_count=book_count
        )

@app.route('/add_book', methods=['POST'])
@login_required
@admin_required
def add_book():
    book = Book(
        title=request.form['title'],
        author=request.form['author'],
        total_copies=int(request.form['total_copies']),
        available_copies=int(request.form['total_copies'])
    )
    db.session.add(book)
    db.session.commit()
    flash("Book added successfully.")
    return redirect(url_for('dashboard'))

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        flash("Book not found.")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        new_title = request.form['title']
        new_author = request.form['author']
        new_total_copies = int(request.form['total_copies'])
        diff = new_total_copies - book.total_copies
        book.title = new_title
        book.author = new_author
        book.total_copies = new_total_copies
        book.available_copies += diff
        if book.available_copies < 0:
            book.available_copies = 0
        db.session.commit()
        flash("Book updated successfully.")
        return redirect(url_for('dashboard'))
    return render_template('edit_book.html', book=book)

@app.route('/delete_book/<int:book_id>')
@login_required
@admin_required
def delete_book(book_id):
    Book.query.filter_by(id=book_id).delete()
    db.session.commit()
    flash("Book deleted successfully.")
    return redirect(url_for('dashboard'))

@app.route('/borrow/<int:book_id>')
@login_required
def borrow(book_id):
    if session['role'] != 'user':
        flash("Only users can borrow books.")
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    book = Book.query.get(book_id)
    if book.available_copies <= 0:
        flash("No copies available. Use the 'Request to Borrow' button.")
        return redirect(url_for('dashboard'))
    already_borrowed = Borrow.query.filter_by(user_id=user_id, book_id=book_id).first()
    if already_borrowed:
        flash("You already borrowed this book.")
        return redirect(url_for('dashboard'))
    borrow = Borrow(user_id=user_id, book_id=book_id, borrow_date=datetime.now())
    book.available_copies -= 1
    db.session.add(borrow)
    db.session.commit()
    flash(f"Borrowed '{book.title}' successfully.")
    return redirect(url_for('dashboard'))

@app.route('/request_waitlist/<int:book_id>', methods=['POST'])
@login_required
def request_waitlist(book_id):
    if session.get('role') != 'user':
        flash("Only users can request books.")
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    book = Book.query.get(book_id)
    existing = Waitlist.query.filter_by(user_id=user_id, book_id=book_id).first()
    if existing:
        flash("You're already in the waitlist.")
        return redirect(url_for('dashboard'))
    waitlist = Waitlist(user_id=user_id, book_id=book_id)
    db.session.add(waitlist)
    db.session.commit()
    flash(f"No copies available. Added to waitlist for '{book.title}'.")
    return redirect(url_for('dashboard'))
@app.route('/return/<int:borrow_id>')
@login_required
def return_book(borrow_id):
    borrow = Borrow.query.get(borrow_id)
    if not borrow or borrow.user_id != session['user_id']:
        flash("Invalid operation.")
        return redirect(url_for('dashboard'))

    book = Book.query.get(borrow.book_id)
    fine = 0
    days = (datetime.now() - borrow.borrow_date).days
    if days > 5:
        fine = (days - 5) * 5

    book.available_copies += 1
    db.session.delete(borrow)

    # Waitlist logic
    next_wait = Waitlist.query.filter_by(book_id=book.id).order_by(Waitlist.request_date).first()
    if next_wait:
        next_user = User.query.get(next_wait.user_id)
        new_borrow = Borrow(user_id=next_user.id, book_id=book.id, borrow_date=datetime.now())
        book.available_copies -= 1
        db.session.add(new_borrow)
        db.session.delete(next_wait)

        try:
            msg = Message(
                subject="Book Allocated to You",
                sender=app.config['MAIL_USERNAME'],
                recipients=[next_user.email]
            )
            msg.body = f"""
Hi {next_user.name},

The book you requested ('{book.title}') is now available and has been automatically allocated to you.

You must return it within 1 day to avoid a fine.

Happy reading!
Yugala(Admmin)
Library Management System
"""
            mail.send(msg)
            flash("Book assigned to next waitlist user and email sent.")
        except Exception as e:
            print("Failed to send email:", e)
            flash("Book assigned to next user but failed to send email.")
    else:
        flash("Book returned. No one in waitlist.")

    db.session.commit()
    flash(f"Returned '{book.title}'. Fine: ₹{fine}")
    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('login'))


def check_borrow_reminders():
    borrows = Borrow.query.all()
    for borrow in borrows:
        due_date = borrow.borrow_date.date() + timedelta(days=5)  
        if (due_date - datetime.now().date()).days == 5:
            user = User.query.get(borrow.user_id)
            book = Book.query.get(borrow.book_id)
            if user and book: 
                try:
                    msg = Message(
                        "Reminder: Return Book Tomorrow",
                        # Use MAIL_DEFAULT_SENDER from app config
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[user.email]
                    )
                    msg.body = f"Hi {user.name},\n\nThis is a reminder to return '{book.title}' by tomorrow.\n\n- Library" 
                    mail.send(msg)
 
                    print(f"Reminder email sent to {user.email} for book '{book.title}'") 
                except Exception as e:
                    logging.error(f"Failed to send reminder to {user.email} for book '{book.title}': {e}") 
 
 
scheduler = BackgroundScheduler()
scheduler.add_job(check_borrow_reminders, 'interval', hours=24)
scheduler.start()
 

if __name__ == '__main__':
    app.run(debug=True)
