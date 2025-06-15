
from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
import logging

app = Flask(__name__)
app.secret_key = 'secret-key'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database4.db'

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'yugalapatibandla@gmail.com'
#https://myaccount.google.com/apppasswords
app.config['MAIL_PASSWORD'] = 'gfcb iege lavw quwa'
#setting Default sender
app.config['MAIL_DEFAULT_SENDER'] = 'yugalapatibandla@gmail.com'

mail = Mail(app)
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    role = db.Column(db.String(10))
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(100), unique=True)
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

class FineHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    fine_amount = db.Column(db.Integer)
    date_paid = db.Column(db.DateTime, default=datetime.now)
   

    user = db.relationship('User', backref='fines')
    book = db.relationship('Book', backref='fines')

# Decorators
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
#Routes
@app.route('/')
def home():
    return redirect(url_for('login'))
#For initializiing Database
@app.route('/init_db')
def init_db():
    db.create_all()
    return "Database initialized!"
#Register New user
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
#Login Route for member login
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
#User and Admin Dashboards
@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    if session['role'] == 'admin':
        members = User.query.filter_by(role='user').all()
        books = Book.query.all()
        member_count = len(members)
        book_count = len(books)
        return render_template('dashboard_admin.html', user=user, members=members, books=books,  member_count=member_count,
            book_count=book_count,fines=FineHistory.query.all())
    else:
        books = Book.query.all()
        borrowed = Borrow.query.filter_by(user_id=user.id).all()
        fines = FineHistory.query.filter_by(user_id=user.id).all()
        book_count = len(books)
        return render_template('dashboard_user.html', user=user, books=books,book_count=book_count,borrowed=borrowed, fines=fines)
# About Route
@app.route('/about')
@login_required
def about():
    return render_template('about.html')
#Add book route for Admin
@app.route('/add_book', methods=['GET', 'POST'])
@admin_required
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        total_copies = int(request.form['total_copies'])
        book = Book(title=title, author=author, total_copies=total_copies, available_copies=total_copies)
        db.session.add(book)
        db.session.commit()
        flash("Book added successfully.")
        return redirect(url_for('dashboard'))
#Edit book Route for Admin
@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        flash("Book not found.")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        new_total_copies = int(request.form['total_copies'])
        diff = new_total_copies - book.total_copies
        book.total_copies = new_total_copies
        book.available_copies += diff
        if book.available_copies < 0:
            book.available_copies = 0
        db.session.commit()
        flash("Book updated successfully.")
        return redirect(url_for('dashboard'))
    return render_template('edit_book.html', book=book)
#Delete book route for admin
@app.route('/delete_book/<int:book_id>')
@login_required
@admin_required
def delete_book(book_id):
    Book.query.filter_by(id=book_id).delete()
    db.session.commit()
    flash("Book deleted successfully.")
    return redirect(url_for('dashboard'))   

#Borrow route for User
@app.route('/borrow/<int:book_id>')
@login_required
def borrow(book_id):
    if session['role'] != 'user':
        flash("Only users can borrow books.")
        return redirect(url_for('dashboard'))
    user_id = session['user_id']
    book = Book.query.get(book_id)
    if book.available_copies <= 0:
        flash("No copies available.")
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
#Waitlist Route for User
@app.route('/waitlist/<int:book_id>', methods=['GET', 'POST'])
@login_required
def request_waitlist(book_id):
    if session.get('role') != 'user':
        flash("Only users can request waitlist.")
        return redirect(url_for('dashboard'))
    
    user_id = session['user_id']
    book = Book.query.get(book_id)
    if not book:
        flash("Book not found.")
        return redirect(url_for('dashboard'))
    
    # Check if already in waitlist
    existing = Waitlist.query.filter_by(user_id=user_id, book_id=book_id).first()
    if existing:
        flash("You have already requested to waitlist this book.")
        return redirect(url_for('dashboard'))
    
    wait_entry = Waitlist(user_id=user_id, book_id=book_id)
    db.session.add(wait_entry)
    db.session.commit()
    flash(f"You have been added to the waitlist for '{book.title}'. You will be notified when it's available.")
    return redirect(url_for('dashboard'))

#Return route for user
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

    # Fine calculation if returned late (after 2 days)
    if days > 1:
        fine = (days - 1) * 5

        fine_entry = FineHistory(user_id=session['user_id'], book_id=book.id, fine_amount=fine)
        db.session.add(fine_entry)

    
    book.available_copies += 1
    db.session.delete(borrow)
    db.session.commit()

    # Check waitlist
    next_wait = Waitlist.query.filter_by(book_id=book.id).order_by(Waitlist.request_date).first()
    if next_wait:
        next_user = User.query.get(next_wait.user_id)

        # Check if the waitlist user already has this book
        already_borrowed = Borrow.query.filter_by(user_id=next_user.id, book_id=book.id).first()
        if already_borrowed:
            
            db.session.delete(next_wait)
            db.session.commit()
            flash(f"Book returned. {next_user.name} already borrowed this book. Skipping waitlist.")
            return redirect(url_for('dashboard'))

        # Allocate book to next waitlist user
        new_borrow = Borrow(user_id=next_user.id, book_id=book.id, borrow_date=datetime.now())
        book.available_copies -= 1  
        db.session.add(new_borrow)
        db.session.delete(next_wait)
        db.session.commit()

        # Send email
        try:
            msg = Message(
                subject="Book Allocated to You",
                sender=app.config['MAIL_USERNAME'],
                recipients=[next_user.email]
            )
            msg.body = f"""
Hi {next_user.name},

The book you requested ('{book.title}') is now available and has been assigned to you.

Please check your dashboard.

Happy reading!
Yugala (Admin)
Library Management System
"""
            mail.send(msg)
            flash(f"Book returned. Assigned to next waitlisted user: {next_user.name}. Email sent.")
            print(f"[INFO] Book '{book.title}' assigned to {next_user.name} ({next_user.email}) from waitlist.")
        except Exception as e:
            logging.error(f"Failed to send email to {next_user.email}: {e}")
            flash("Book assigned to waitlist user, but failed to send email.")
    else:
        flash("Book returned. No one in the waitlist.")

    # Show fine message
    if fine > 0:
        flash(f"Returned '{book.title}'. Fine: ₹{fine}")
    else:
        flash(f"Returned '{book.title}' successfully.")
    
    return redirect(url_for('dashboard'))



#Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.")
    return redirect(url_for('login'))
#scheduled borrow remainders 
def check_borrow_reminders():
    logging.info("Running scheduled borrow reminders check...")
    borrows = Borrow.query.all()
    for borrow in borrows:
        due_date = borrow.borrow_date.date() + timedelta(days=2)  # Loan period = 2 days
        days_until_due = (due_date - datetime.now().date()).days
        logging.info(f"Borrow ID {borrow.id}: due in {days_until_due} days")

        if days_until_due == 1:
            user = User.query.get(borrow.user_id)
            book = Book.query.get(borrow.book_id)
            if user and book:
                try:
                    msg = Message(
                        "Reminder: Return Book Tomorrow",
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[user.email]
                    )
                    msg.body = f"Hi {user.name},\n\nReminder to return '{book.title}' by tomorrow to avoid fines."
                    mail.send(msg)
                    logging.info(f"Reminder sent to {user.email} for book '{book.title}'")
                except Exception as e:
                    logging.error(f"Failed to send reminder to {user.email} for '{book.title}': {e}")

# APScheduler to run every 24 hours
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler()
scheduler.add_job(check_borrow_reminders, 'interval', hours=24)
scheduler.start()
#For sending mails after manually trriggered
@app.route('/run_reminder_now')
def run_reminder_now():
    check_borrow_reminders()
    return "Reminder function executed."

if __name__ == '__main__':
    app.run(debug=True)