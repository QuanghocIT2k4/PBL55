# accounts/tests.py
from django.test import TestCase
from django.db import IntegrityError # Để kiểm tra lỗi unique constraint
from rest_framework.exceptions import ValidationError # Để kiểm tra lỗi validation của DRF

# Import các thành phần cần test từ app accounts
from .models import CustomUser
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer

# Import thư viện hash mật khẩu
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Khởi tạo PasswordHasher một lần
ph = PasswordHasher()

# --- Test cho Model CustomUser ---
class CustomUserModelTest(TestCase):

    def setUp(self):
        """Tạo dữ liệu dùng chung cho các test case model."""
        self.hashed_password = ph.hash('TestPass@123')
        self.user_data = {
            'email': 'testuser@example.com',
            'password_hash': self.hashed_password,
            'first_name': 'Test',
            'last_name': 'User',
        }
        self.admin_data = {
            'email': 'admin@example.com',
            'password_hash': ph.hash('AdminPass@123'),
            'user_type': 'ADMIN'
        }

    def test_create_regular_user(self):
        """Kiểm tra tạo User thường thành công."""
        user = CustomUser.objects.create(**self.user_data)
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(user.email, 'testuser@example.com')
        self.assertEqual(user.user_type, 'REGULAR') # Kiểm tra default
        self.assertTrue(user.is_active)       # Kiểm tra default
        self.assertTrue(ph.verify(user.password_hash, 'TestPass@123')) # Kiểm tra hash
        self.assertTrue(user.is_regular_user)
        self.assertFalse(user.is_admin)
        self.assertEqual(str(user), 'testuser@example.com (Người dùng thường)')

    def test_create_admin_user(self):
        """Kiểm tra tạo Admin User thành công."""
        admin = CustomUser.objects.create(**self.admin_data)
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertEqual(admin.user_type, 'ADMIN')
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_regular_user)
        self.assertEqual(str(admin), 'admin@example.com (Quản trị viên)')

    def test_email_is_unique(self):
        """Kiểm tra ràng buộc unique của email."""
        CustomUser.objects.create(**self.user_data) # Tạo user đầu tiên
        # Thử tạo user thứ hai với cùng email, mong đợi lỗi IntegrityError
        with self.assertRaises(IntegrityError):
            CustomUser.objects.create(email='testuser@example.com', password_hash=ph.hash('anotherpass'))

# --- Test cho UserSerializer ---
class UserSerializerTest(TestCase):

    def setUp(self):
        """Tạo user mẫu để test serialization."""
        self.user = CustomUser.objects.create(
            email='serializer@example.com',
            password_hash=ph.hash('serializerpass'),
            first_name='Serial',
            last_name='Izer',
            user_type='ADMIN'
        )
        # Tạo serializer từ instance user
        self.serializer = UserSerializer(instance=self.user)

    def test_serialization_contains_expected_fields(self):
        """Kiểm tra các trường đúng được serialize."""
        data = self.serializer.data
        expected_keys = {
            'id', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display', 'is_active',
            'created_at', 'updated_at'
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_serialization_password_hash_excluded(self):
        """Kiểm tra password_hash không bị lộ ra."""
        data = self.serializer.data
        self.assertNotIn('password_hash', data)

    def test_serialization_field_content(self):
        """Kiểm tra nội dung các trường được serialize đúng."""
        data = self.serializer.data
        self.assertEqual(data['email'], self.user.email)
        self.assertEqual(data['first_name'], self.user.first_name)
        self.assertEqual(data['user_type'], 'ADMIN')
        self.assertEqual(data['user_type_display'], 'Quản trị viên') # Kiểm tra source='get_..._display'


# --- Test cho RegisterSerializer ---
class RegisterSerializerTest(TestCase):

    def setUp(self):
        """Chuẩn bị dữ liệu test cho RegisterSerializer."""
        self.valid_data_regular = {
            'email': 'newreg@example.com',
            'password': 'NewStrongPass1!',
            'password2': 'NewStrongPass1!',
            'first_name': 'New',
            'last_name': 'Regular'
            # user_type sẽ mặc định là REGULAR
        }
        self.valid_data_admin = {
            'email': 'newadm@example.com',
            'password': 'NewAdminPass1!',
            'password2': 'NewAdminPass1!',
            'user_type': 'ADMIN' # Chỉ định tạo admin
        }
        self.invalid_data_mismatch = {
            'email': 'mismatch@example.com',
            'password': 'password1',
            'password2': 'password2'
        }
        self.invalid_data_short_pw = {
            'email': 'shortpw@example.com',
            'password': 'short',
            'password2': 'short'
        }
        # Tạo user trước để test email trùng
        CustomUser.objects.create(email='existing@example.com', password_hash=ph.hash('exist'))
        self.invalid_data_existing_email = {
             'email': 'existing@example.com',
             'password': 'password123',
             'password2': 'password123'
        }

    def test_valid_regular_user_data(self):
        """Kiểm tra dữ liệu hợp lệ cho user thường."""
        serializer = RegisterSerializer(data=self.valid_data_regular)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_admin_user_data(self):
        """Kiểm tra dữ liệu hợp lệ cho admin."""
        serializer = RegisterSerializer(data=self.valid_data_admin)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_password_mismatch(self):
        """Kiểm tra lỗi validation khi mật khẩu không khớp."""
        serializer = RegisterSerializer(data=self.invalid_data_mismatch)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)
        self.assertEqual(len(serializer.errors['password']), 1) # Chỉ có 1 lỗi về password

    def test_invalid_short_password(self):
        """Kiểm tra lỗi validation khi mật khẩu quá ngắn."""
        serializer = RegisterSerializer(data=self.invalid_data_short_pw)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_invalid_existing_email(self):
        """Kiểm tra lỗi validation khi email đã tồn tại."""
        serializer = RegisterSerializer(data=self.invalid_data_existing_email)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_create_regular_user_via_serializer(self):
        """Kiểm tra hàm create tạo user thường và hash password."""
        serializer = RegisterSerializer(data=self.valid_data_regular)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertIsInstance(user, CustomUser)
        self.assertEqual(user.email, self.valid_data_regular['email'])
        self.assertEqual(user.user_type, 'REGULAR') # Kiểm tra default khi tạo
        self.assertNotEqual(user.password_hash, self.valid_data_regular['password']) # Đã hash
        self.assertTrue(ph.verify(user.password_hash, self.valid_data_regular['password'])) # Verify thành công

    def test_create_admin_user_via_serializer(self):
        """Kiểm tra hàm create tạo admin user và hash password."""
        serializer = RegisterSerializer(data=self.valid_data_admin)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertIsInstance(user, CustomUser)
        self.assertEqual(user.email, self.valid_data_admin['email'])
        self.assertEqual(user.user_type, 'ADMIN') # Kiểm tra type đã set
        self.assertTrue(ph.verify(user.password_hash, self.valid_data_admin['password']))


# --- Test cho LoginSerializer ---
class LoginSerializerTest(TestCase):

    def test_valid_login_data(self):
        """Kiểm tra dữ liệu đăng nhập hợp lệ (có đủ trường)."""
        data = {'email': 'login@example.com', 'password': 'password123'}
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_missing_email(self):
        """Kiểm tra lỗi khi thiếu email."""
        data = {'password': 'password123'}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_missing_password(self):
        """Kiểm tra lỗi khi thiếu password."""
        data = {'email': 'login@example.com'}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_invalid_email_format(self):
        """Kiểm tra lỗi khi email sai định dạng."""
        data = {'email': 'not-an-email', 'password': 'password123'}
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)