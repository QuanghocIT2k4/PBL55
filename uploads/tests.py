# uploads/tests.py
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.timezone import now # Import now để so sánh thời gian nếu cần
import os

# Import models và serializers từ app uploads và accounts
from .models import UserUpload
from .serializers import UserUploadSerializer
from accounts.models import CustomUser # Cần để tạo user cho upload

# Import thư viện hash
from argon2 import PasswordHasher
ph = PasswordHasher()

class UserUploadModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Tạo user một lần cho cả lớp test model
        cls.hashed_password = ph.hash('testpassword')
        cls.user = CustomUser.objects.create(
            email='uploadtest@example.com',
            password_hash=cls.hashed_password,
            first_name='Upload',
            last_name='Tester'
        )
        # Tạo file giả
        cls.fake_file_content = b'This is test content.'
        cls.fake_file_name = 'my_test_upload.txt'
        cls.fake_file = SimpleUploadedFile(
            name=cls.fake_file_name,
            content=cls.fake_file_content,
            content_type='text/plain'
        )

    def test_create_user_upload(self):
        """Kiểm tra việc tạo bản ghi UserUpload thành công."""
        initial_count = UserUpload.objects.count()
        upload = UserUpload.objects.create(
            uploaded_by=self.user,
            file=self.fake_file
        )
        self.assertEqual(UserUpload.objects.count(), initial_count + 1)
        self.assertEqual(upload.uploaded_by, self.user)
        # Kiểm tra cấu trúc đường dẫn file được lưu
        self.assertTrue(upload.file.name.startswith(f'user_uploads/{self.user.id}/user_{self.user.id}_'))
        self.assertTrue(upload.file.name.endswith('.txt'))
        # Kiểm tra nội dung __str__
        upload_str = str(upload)
        self.assertIn(f" by {self.user.email}", upload_str)
        self.assertIn(upload.upload_time.strftime('%Y-%m-%d %H:%M'), upload_str)
        # Kiểm tra phần tên file (có thể không cần quá chính xác do có UUID)
        self.assertTrue(upload_str.startswith(f"user_{self.user.id}_"))

    def test_file_path_generation(self):
        """Kiểm tra đường dẫn file được tạo đúng cấu trúc với đuôi file khác."""
        upload = UserUpload.objects.create(
            uploaded_by=self.user,
            file=SimpleUploadedFile('another test file.jpg', b'content', 'image/jpeg')
        )
        expected_path_prefix = f'user_uploads/{self.user.id}/user_{self.user.id}_'
        expected_path_suffix = '.jpg'
        self.assertTrue(upload.file.name.startswith(expected_path_prefix))
        self.assertTrue(upload.file.name.endswith(expected_path_suffix))


class UserUploadSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Tạo dữ liệu cần thiết cho test serializer."""
        cls.user = CustomUser.objects.create(
            email='serializeruser@example.com',
            password_hash=ph.hash('serpass'),
            first_name='Serializer',
            last_name='Upload'
        )
        cls.upload_time_before_create = now() # Ghi lại thời gian trước khi tạo
        cls.upload = UserUpload.objects.create(
            uploaded_by=cls.user,
            file=SimpleUploadedFile('serializer_test.png', b'pngcontent', 'image/png')
        )
        # Tạo mock request nếu serializer cần (ví dụ để build URL tuyệt đối)
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/') # Request GET đơn giản

    def test_serialization_output(self):
        """Kiểm tra dữ liệu trả ra từ serializer."""
        # Truyền context chứa request nếu serializer có thể cần
        serializer = UserUploadSerializer(instance=self.upload, context={'request': self.request})
        data = serializer.data

        # Kiểm tra các key chính
        expected_keys = {'id', 'uploaded_by', 'uploaded_by_info', 'file', 'upload_time'}
        self.assertEqual(set(data.keys()), expected_keys)

        # Kiểm tra các giá trị
        self.assertEqual(data['id'], self.upload.id)
        self.assertEqual(data['uploaded_by'], self.user.id)
        # Kiểm tra đường dẫn tương đối bắt đầu đúng cách
        self.assertTrue(data['file'].startswith(f'user_uploads/{self.user.id}/user_{self.user.id}_'))
        self.assertTrue(data['file'].endswith('.png')) # Kiểm tra đuôi file

        # Kiểm tra dữ liệu lồng của user
        uploaded_by_info = data['uploaded_by_info']
        self.assertEqual(uploaded_by_info['id'], self.user.id)
        self.assertEqual(uploaded_by_info['email'], self.user.email)
        self.assertEqual(uploaded_by_info['first_name'], self.user.first_name)
        self.assertNotIn('password_hash', uploaded_by_info) # Đảm bảo không lộ pass

        # Kiểm tra kiểu dữ liệu thời gian trả về (thường là string ISO format)
        self.assertTrue(isinstance(data['upload_time'], str))


    # Test case này kiểm tra hành vi update khi có read_only_fields
    def test_update_ignores_read_only_fields(self):
        """Kiểm tra khi update, các trường read_only không bị thay đổi."""
        # Lưu lại thời gian upload gốc để so sánh
        original_upload_time = self.upload.upload_time

        serializer = UserUploadSerializer(
            instance=self.upload, # Cập nhật instance hiện có
            data={
                # Không cần gửi 'file' vì không bắt buộc khi update partial
                # Cố gắng gửi giá trị cho các trường read_only:
                'uploaded_by': 999, # ID user không tồn tại hoặc khác
                'upload_time': '2000-01-01T01:01:01Z' # Thời gian không hợp lệ
            },
            partial=True # Cho phép cập nhật một phần
        )
        # Serializer vẫn valid vì các trường read_only bị bỏ qua khi validate input update
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_instance = serializer.save()

        # Nạp lại đối tượng từ DB để chắc chắn
        updated_instance.refresh_from_db()

        # Kiểm tra xem các trường read_only có bị thay đổi không
        self.assertEqual(updated_instance.uploaded_by, self.user) # Phải là user gốc
        self.assertEqual(updated_instance.upload_time, original_upload_time) # Phải là thời gian gốc