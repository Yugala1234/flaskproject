import unittest
from project2 import app, db, User, Book, Borrow, Waitlist, FineHistory
from flask import session
from werkzeug.security import generate_password_hash

class LibrarySystemTestCase(unittest.TestCase):

    def setUp(self):
        # Configure the app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()
        db.create_all()

        # Create test users with hashed passwords
        self.admin = User(name='Admin', role='admin', username='admin',
                          email='admin@test.com', password=generate_password_hash('admin'))
        self.user = User(name='User', role='user', username='user',
                         email='user@test.com', password=generate_password_hash('user'))

        db.session.add(self.admin)
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, username, password):
        return self.app.post('/login', data=dict(username=username, password=password), follow_redirects=True)

    def test_home_redirect(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_register_get(self):
        response = self.app.get('/register')
        self.assertEqual(response.status_code, 200)

    def test_register_post(self):
        response = self.app.post('/register', data=dict(
            name='NewUser',
            role='user',
            username='newuser',
            email='newuser@test.com',
            password='newpass'
        ), follow_redirects=True)
        self.assertIn(b'Registration successful', response.data)

    def test_login_invalid(self):
        response = self.login('wrong', 'wrong')
        self.assertIn(b'Invalid credentials', response.data)

    def test_login_valid_user(self):
        response = self.login('user', 'user')
        self.assertIn(b'Welcome', response.data)

    def test_dashboard_redirect(self):
        self.login('user', 'user')
        response = self.app.get('/dashboard', follow_redirects=True)
        self.assertIn('User Dashboard'.lower(), response.data.decode().lower())

    def test_add_book_as_admin(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.admin.id
            sess['role'] = 'admin'
        response = self.app.post('/add_book', data=dict(
            title='Book1',
            author='Author1',
            total_copies='3'
        ), follow_redirects=True)
        self.assertIn(b'Book added successfully', response.data)

    def test_add_book_as_user_forbidden(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['role'] = 'user'
        response = self.app.post('/add_book', data=dict(
            title='Book1',
            author='Author1',
            total_copies='3'
        ), follow_redirects=True)
        self.assertIn(b'Admin access only', response.data)

    def test_logout(self):
        self.login('user', 'user')
        response = self.app.get('/logout', follow_redirects=True)
        self.assertIn(b'Logged out', response.data)

    def test_init_db(self):
        response = self.app.get('/init_db')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Database initialized', response.data)

    def test_about_authenticated(self):
        with self.app.session_transaction() as sess:
            sess['user_id'] = self.user.id
            sess['role'] = 'user'
        response = self.app.get('/about')
        self.assertEqual(response.status_code, 200)

    def test_run_reminder_now(self):
        response = self.app.get('/run_reminder_now')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Reminder function executed', response.data)

if __name__ == '__main__':
    unittest.main()
