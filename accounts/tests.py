from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import User
from .models import CustomUser

class AuthenticationViewsTestCase(TestCase):
    """Test cases for authentication views and middleware."""
    
    def setUp(self):
        self.client = Client()
        self.user_model = get_user_model()
        
        # Create test users
        self.admin_user = self.user_model.objects.create_user(
            username='admin_test',
            email='admin@test.com',
            password='testpass123',
            role='ADMIN'
        )
        
        self.driver_user = self.user_model.objects.create_user(
            username='driver_test',
            email='driver@test.com',
            password='testpass123',
            role='DRIVER'
        )
        
        self.suspended_user = self.user_model.objects.create_user(
            username='suspended_test',
            email='suspended@test.com',
            password='testpass123',
            role='SUSPENDED'
        )
    
    def test_login_view_get(self):
        """Test login view renders correctly."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'login')
    
    def test_valid_login(self):
        """Test successful login with valid credentials."""
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
    
    def test_invalid_login(self):
        """Test login failure with invalid credentials."""
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Stay on login page
    
    def test_suspended_user_middleware(self):
        """Test that suspended users are automatically logged out."""
        # Login as suspended user
        self.client.login(username='suspended_test', password='testpass123')
        
        # Try to access a protected view
        response = self.client.get('/dashboard/')
        
        # Should be redirected to login due to middleware
        self.assertEqual(response.status_code, 302)
    
    def test_role_based_access(self):
        """Test that users can only access appropriate views based on role."""
        # Login as driver
        self.client.login(username='driver_test', password='testpass123')
        
        # Try to access admin view - should be denied
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_logout_functionality(self):
        """Test logout clears session properly."""
        self.client.login(username='admin_test', password='testpass123')
        
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        
        # Verify user is logged out
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
