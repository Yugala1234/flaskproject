import unittest
from project2 import app, db, User, Book
from werkzeug.security import generate_password_hash

class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.app.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def register_user(self, name, role, username, email, password):
        with app.app_context():
            user = User(name=name, role=role, username=username, email=email, password=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            return user

    def add_book_helper(self, title, author, total_copies):
        with app.app_context():
            book = Book(title=title, author=author, total_copies=total_copies, available_copies=total_copies)
            db.session.add(book)
            db.session.commit()
            return book

    def test_register(self):
        # Test successful registration
        response = self.app.post('/register', data=dict(
            name='Test User',
            role='user',
            username='testuser',
            email='test@example.com',
            password='password'
        ), follow_redirects=True)
        self.assertIn(b'Registration successful. Please login.', response.data)

        # Test registration with existing username
        response = self.app.post('/register', data=dict(
            name='Another User',
            role='user',
            username='testuser',
            email='another@example.com',
            password='password'
        ), follow_redirects=True)
        self.assertIn(b'Username already exists.', response.data)

    def test_add_book(self):
        # Create an admin user and log in
        self.register_user('Admin User', 'admin', 'adminuser', 'admin@example.com', 'password')
        self.login('adminuser', 'password')

        # Test successful book addition
        response = self.app.post('/add_book', data=dict(
            title='Test Book',
            author='Test Author',
            total_copies='5'
        ), follow_redirects=True)
        self.assertIn(b'Book added successfully.', response.data)

        # Verify the book was added to the database
        with app.app_context():
            book = Book.query.filter_by(title='Test Book').first()
            self.assertIsNotNone(book)
            self.assertEqual(book.total_copies, 5)
            self.assertEqual(book.available_copies, 5)

        # Log out the admin
        self.logout()

        # Create a regular user and log in
        self.register_user('Regular User', 'user', 'regularuser', 'user@example.com', 'password')
        self.login('regularuser', 'password')

        # Test adding a book as a regular user (should be denied)
        response = self.app.post('/add_book', data=dict(
            title='Another Book',
            author='Another Author',
            total_copies='3'
        ), follow_redirects=True)
        self.assertIn(b'Admin access only.', response.data)

        # Verify the book was not added to the database
        with app.app_context():
            book = Book.query.filter_by(title='Another Book').first()
            self.assertIsNone(book)


        def test_edit_book(self):
        # Create an admin user and log in
        self.register_user('Admin User', 'admin', 'adminuser', 'admin@example.com', 'password')
        self.login('adminuser', 'password')
    
        # Add a book to edit within an app context
        with app.app_context():
            book = self.add_book_helper('Book to Edit', 'Original Author', 10)
            book_id = book.id # Get the book ID while within the context
    
        # Test successful book editing
        response = self.app.post(f'/edit_book/{book_id}', data=dict(
            title='Edited Book Title',
            author='Edited Author',
            total_copies='15'
        ), follow_redirects=True)
        self.assertIn(b'Book updated successfully.', response.data)
    
        # Verify the book was updated in the database within a new app context
        with app.app_context():
            updated_book = Book.query.get(book_id)
            self.assertIsNotNone(updated_book)
            self.assertEqual(updated_book.title, 'Edited Book Title')
            self.assertEqual(updated_book.author, 'Edited Author')
            self.assertEqual(updated_book.total_copies, 15)
            # Available copies should be updated based on the difference
            self.assertEqual(updated_book.available_copies, 15) # Assuming no borrows yet
    
        # Log out the admin
        self.logout()
    
        # Create a regular user and log in
        self.register_user('Regular User', 'user', 'regularuser', 'user@example.com', 'password')
        self.login('regularuser', 'password')
    
        # Test editing a book as a regular user (should be denied)
        response = self.app.post(f'/edit_book/{book_id}', data=dict(
            title='Attempted Edit',
            author='Attempted Author',
            total_copies='20'
        ), follow_redirects=True)
        self.assertIn(b'Admin access only.', response.data)
    
        # Verify the book was not changed within a new app context
        with app.app_context():
            unchanged_book = Book.query.get(book_id)
            self.assertEqual(unchanged_book.title, 'Edited Book Title')
    
    
        # Log out the regular user
        self.logout()
    
        # Test editing a non-existent book as an admin
        self.login('adminuser', 'password')
        response = self.app.post('/edit_book/999', data=dict(
            title='Nonexistent Edit',
            author='Nonexistent Author',
            total_copies='5'
        ), follow_redirects=True)
        self.assertIn(b'Book not found.', response.data)
        
    
    if __name__ == '__main__':
    unittest.main()
