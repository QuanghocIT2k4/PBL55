# insect_library/tests.py
from django.urls import reverse # Để tạo URL từ tên của nó
from rest_framework import status
from rest_framework.test import APITestCase, TestCase # Dùng APITestCase để test API endpoint

# Import models và serializers
from .models import InsectReference
from .serializers import InsectReferenceSerializer

# Import model user và thư viện hash để tạo user test
from accounts.models import CustomUser
from argon2 import PasswordHasher
ph = PasswordHasher()

class InsectReferenceModelTest(TestCase):
    """Test cho model InsectReference."""

    def test_create_insect_reference(self):
        """Kiểm tra tạo đối tượng thành công."""
        ref = InsectReference.objects.create(
            name='TestRefInsect',
            scientific_name='Testus scientificus',
            description='A test insect.'
        )
        self.assertEqual(InsectReference.objects.count(), 1)
        self.assertEqual(ref.name, 'TestRefInsect')
        self.assertEqual(str(ref), 'TestRefInsect')

    def test_name_unique_constraint(self):
        """Kiểm tra ràng buộc unique của trường name."""
        InsectReference.objects.create(name='UniqueInsect')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            InsectReference.objects.create(name='UniqueInsect')


class InsectReferenceSerializerTest(TestCase):
    """Test cho InsectReferenceSerializer."""

    def setUp(self):
        self.insect_data = {
            'name': 'SerializerInsectRef',
            'scientific_name': 'Serializerus scientificus',
            'description': 'Testing serializer.',
            'habitat': 'Test Habitat',
            'host_plants': 'Test Plants',
            'treatment': 'Test Treatment',
            'active_season': 'Test Season'
        }
        self.insect = InsectReference.objects.create(**self.insect_data)
        self.serializer = InsectReferenceSerializer(instance=self.insect)

    def test_contains_expected_fields(self):
        """Kiểm tra serializer chứa đủ các trường."""
        data = self.serializer.data
        expected_keys = {
            'id', 'name', 'scientific_name', 'description', 'habitat',
            'host_plants', 'treatment', 'active_season',
            'created_at', 'updated_at'
            # Thêm 'reference_image' nếu bạn dùng ImageField
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_serialization_data_correct(self):
        """Kiểm tra dữ liệu serialize ra là chính xác."""
        data = self.serializer.data
        self.assertEqual(data['name'], self.insect_data['name'])
        self.assertEqual(data['description'], self.insect_data['description'])

    def test_deserialization_valid_data(self):
        """Kiểm tra deserialize dữ liệu hợp lệ để tạo mới."""
        new_data = {
            'name': 'NewInsectViaSerializer',
            'description': 'Created via serializer.'
            # Các trường khác có thể là null/blank
        }
        serializer = InsectReferenceSerializer(data=new_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_deserialization_invalid_data_missing_name(self):
        """Kiểm tra lỗi khi thiếu trường bắt buộc 'name'."""
        invalid_data = {'description': 'Missing name.'}
        serializer = InsectReferenceSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)


class InsectReferenceViewSetTest(APITestCase):
    """Test cho API endpoint của InsectReference (ViewSet)."""

    @classmethod
    def setUpTestData(cls):
        """Tạo user Admin và User thường để test quyền."""
        cls.admin_user = CustomUser.objects.create(
            email='lib_admin@example.com',
            password_hash=ph.hash('libadminpass'),
            user_type='ADMIN', is_active=True
        )
        cls.regular_user = CustomUser.objects.create(
            email='lib_user@example.com',
            password_hash=ph.hash('libuserpass'),
            user_type='REGULAR', is_active=True
        )
        # Tạo một vài InsectReference mẫu
        cls.ref1 = InsectReference.objects.create(name='RefInsect 1', description='Desc 1')
        cls.ref2 = InsectReference.objects.create(name='RefInsect 2', description='Desc 2')

        # URL names (giả định basename='insect-reference' trong urls.py)
        cls.list_create_url = reverse('insect-reference-list') # URL cho list và create
        cls.detail_url = lambda pk: reverse('insect-reference-detail', kwargs={'pk': pk}) # URL cho retrieve, update, delete

    def _get_tokens(self, email, password):
        """Helper để lấy access token."""
        response = self.client.post(reverse('accounts:user_login'), {'email': email, 'password': password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['access']

    def setUp(self):
        """Lấy token trước mỗi test."""
        self.admin_token = self._get_tokens('lib_admin@example.com', 'libadminpass')
        self.user_token = self._get_tokens('lib_user@example.com', 'libuserpass')

    # --- Test GET (List/Retrieve) ---
    def test_list_insect_references_authenticated_user(self):
        """User đăng nhập có thể xem danh sách."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Hoặc số lượng đúng nếu có phân trang

    def test_retrieve_insect_reference_authenticated_user(self):
        """User đăng nhập có thể xem chi tiết."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.get(self.detail_url(self.ref1.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.ref1.name)

    def test_list_insect_references_unauthenticated(self):
        """User chưa đăng nhập không thể xem (nếu dùng IsAuthenticatedCustom)."""
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Test POST (Create) ---
    def test_create_insect_reference_admin(self):
        """Admin có thể tạo mới."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        data = {'name': 'New By Admin', 'description': 'Admin created'}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InsectReference.objects.count(), 3)
        self.assertEqual(response.data['name'], 'New By Admin')

    def test_create_insect_reference_regular_user_forbidden(self):
        """User thường không thể tạo mới."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        data = {'name': 'Attempt By User', 'description': 'User should fail'}
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Test PUT/PATCH (Update) ---
    def test_update_insect_reference_admin(self):
        """Admin có thể cập nhật."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        data = {'description': 'Updated by Admin'}
        response = self.client.patch(self.detail_url(self.ref1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ref1.refresh_from_db()
        self.assertEqual(self.ref1.description, 'Updated by Admin')

    def test_update_insect_reference_regular_user_forbidden(self):
        """User thường không thể cập nhật."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        data = {'description': 'User cannot update'}
        response = self.client.patch(self.detail_url(self.ref1.pk), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Test DELETE ---
    def test_delete_insect_reference_admin(self):
        """Admin có thể xóa."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        initial_count = InsectReference.objects.count()
        response = self.client.delete(self.detail_url(self.ref1.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(InsectReference.objects.count(), initial_count - 1)

    def test_delete_insect_reference_regular_user_forbidden(self):
        """User thường không thể xóa."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.user_token}')
        response = self.client.delete(self.detail_url(self.ref1.pk))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)