import unittest
from project2 import app, db, User
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

    def test_login(self):
        # Create a test user
        with app.app_context():
            user = User(name='Test User', role='user', username='testuser', email='test@example.com', password=generate_password_hash('password'))
            db.session.add(user)
            db.session.commit()

        # Test successful login
        response = self.app.post('/login', data=dict(
            username='testuser',
            password='password'
        ), follow_redirects=True)
        self.assertIn(b'Welcome, Test User!', response.data)
        with self.app as c:
            self.assertIn('user_id', c.session)
            self.assertIn('role', c.session)
            self.assertEqual(c.session['role'], 'user')


        # Test login with incorrect password
        response = self.app.post('/login', data=dict(
            username='testuser',
            password='wrongpassword'
        ), follow_redirects=True)
        self.assertIn(b'Invalid credentials.', response.data)
        with self.app as c:
            self.assertNotIn('user_id', c.session)
            self.assertNotIn('role', c.session)

        # Test login with non-existent username
        response = self.app.post('/login', data=dict(
            username='nonexistentuser',
            password='password'
        ), follow_redirects=True)
        self.assertIn(b'Invalid credentials.', response.data)
        with self.app as c:
            self.assertNotIn('user_id', c.session)
            self.assertNotIn('role', c.session)

if __name__ == '__main__':
    unittest.main()
