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
        with app.test_request_context('/login', method='POST', data=dict(
            username='testuser',
            password='password'
        )):
            response = app.preprocess_request()
            # If preprocess_request returns a response, it means a redirect or error occurred
            if response is None:
                # Process the request and get the response
                response = app.dispatch_request()
    
            self.assertIn(b'Welcome, Test User!', response.data)
            from flask import session # Import session within the context
            self.assertIn('user_id', session)
            self.assertIn('role', session)
            self.assertEqual(session['role'], 'user')
    
    
        # Test login with incorrect password
        with app.test_request_context('/login', method='POST', data=dict(
            username='testuser',
            password='wrongpassword'
        )):
            response = app.preprocess_request()
            if response is None:
                response = app.dispatch_request()
    
            self.assertIn(b'Invalid credentials.', response.data)
            from flask import session # Import session within the context
            self.assertNotIn('user_id', session)
            self.assertNotIn('role', session)
    
        # Test login with non-existent username
        with app.test_request_context('/login', method='POST', data=dict(
            username='nonexistentuser',
            password='password'
        )):
            response = app.preprocess_request()
            if response is None:
                response = app.dispatch_request()
    
            self.assertIn(b'Invalid credentials.', response.data)
            from flask import session # Import session within the context
            self.assertNotIn('user_id', session)
            self.assertNotIn('role', session)

        
if __name__ == '__main__':
    unittest.main()
