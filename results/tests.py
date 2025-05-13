# results/tests.py
import base64
from django.test import TestCase, RequestFactory
from django.utils.timezone import now, make_aware
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime

# Import models và serializers cần test
from .models import ProcessingResult, UserUpload # Cần UserUpload để test liên kết
from .serializers import RPiResultInputSerializer, ProcessingResultOutputSerializer
from accounts.models import CustomUser # Cần CustomUser để tạo UserUpload

# Import thư viện hash
from argon2 import PasswordHasher
ph = PasswordHasher()

# --- Test cho Model ProcessingResult ---
class ProcessingResultModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Tạo user và upload gốc để test liên kết
        cls.user = CustomUser.objects.create(email='resulttest@example.com', password_hash=ph.hash('respass'))
        cls.upload = UserUpload.objects.create(
            uploaded_by=cls.user,
            file=SimpleUploadedFile('original.jpg', b'orig', 'image/jpeg')
        )
        cls.processed_image = SimpleUploadedFile('processed.jpg', b'processed', 'image/jpeg')
        cls.timestamp = make_aware(datetime(2025, 5, 5, 15, 0, 0))
        cls.insects_json = [{'name': 'ResultInsect', 'confidence': 0.9}]

    def test_create_result_with_source_upload(self):
        """Kiểm tra tạo kết quả liên kết với upload gốc."""
        initial_count = ProcessingResult.objects.count()
        result = ProcessingResult.objects.create(
            source_upload=self.upload,
            processed_image=self.processed_image,
            detection_timestamp=self.timestamp,
            detected_insects_json=self.insects_json
        )
        self.assertEqual(ProcessingResult.objects.count(), initial_count + 1)
        self.assertEqual(result.source_upload, self.upload)
        self.assertEqual(result.detection_timestamp, self.timestamp)
        self.assertEqual(result.detected_insects_json, self.insects_json)
        self.assertTrue(result.processed_image.name.startswith('processed_results/'))
        expected_str = f"Kết quả cho Upload ID {self.upload.id} nhận lúc {result.received_at.strftime('%Y-%m-%d %H:%M')}"
        self.assertEqual(str(result), expected_str)

    def test_create_result_without_source_upload(self):
        """Kiểm tra tạo kết quả từ camera (source_upload=None)."""
        initial_count = ProcessingResult.objects.count()
        result = ProcessingResult.objects.create(
            source_upload=None, # Quan trọng
            processed_image=SimpleUploadedFile('cam_processed.png', b'cam', 'image/png'),
            detection_timestamp=self.timestamp,
            detected_insects_json=[{'name': 'CameraBug', 'confidence': 0.8}]
        )
        self.assertEqual(ProcessingResult.objects.count(), initial_count + 1)
        self.assertIsNone(result.source_upload)
        expected_str = f"Kết quả từ Camera RPi nhận lúc {result.received_at.strftime('%Y-%m-%d %H:%M')}"
        self.assertEqual(str(result), expected_str)

# --- Test cho RPiResultInputSerializer (Input Validation) ---
class RPiResultInputSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Tạo upload gốc để test validate source_upload_id
        cls.user = CustomUser.objects.create(email='rpiinput@example.com', password_hash=ph.hash('rpi'))
        cls.valid_upload = UserUpload.objects.create(
            uploaded_by=cls.user,
            file=SimpleUploadedFile('rpi_orig.txt', b'rpio', 'text/plain')
        )
        cls.valid_upload_id = cls.valid_upload.id
        # Tạo upload thứ 2 và kết quả để test lỗi "đã tồn tại kết quả"
        cls.upload_with_result = UserUpload.objects.create(
            uploaded_by=cls.user,
            file=SimpleUploadedFile('rpi_orig2.txt', b'rpio2', 'text/plain')
        )
        ProcessingResult.objects.create(
             source_upload=cls.upload_with_result,
             processed_image=SimpleUploadedFile('res2.jpg', b'res2', 'image/jpeg'),
             detection_timestamp=now(),
             detected_insects_json=[{'name':'dummy'}]
        )
        cls.upload_with_result_id = cls.upload_with_result.id

        cls.fake_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        cls.valid_insects = [{"name": "InputInsect", "confidence": 0.85}]

    def test_valid_data_with_source_id(self):
        """Kiểm tra dữ liệu hợp lệ có source_upload_id."""
        data = {
            "image_base64": self.fake_base64,
            "timestamp": "2025-05-06T10:00:00Z",
            "insects": self.valid_insects,
            "source_upload_id": self.valid_upload_id # ID hợp lệ
        }
        serializer = RPiResultInputSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['source_upload_id'], self.valid_upload_id)

    def test_valid_data_with_null_source_id(self):
        """Kiểm tra dữ liệu hợp lệ với source_upload_id = null."""
        data = {
            "image_base64": self.fake_base64,
            "timestamp": "2025-05-06T10:00:00Z",
            "insects": self.valid_insects,
            "source_upload_id": None
        }
        serializer = RPiResultInputSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data['source_upload_id'])

    def test_valid_data_without_source_id(self):
        """Kiểm tra dữ liệu hợp lệ khi không có key source_upload_id."""
        data = {
            "image_base64": self.fake_base64,
            "timestamp": "2025-05-06T10:00:00Z",
            "insects": self.valid_insects
            # source_upload_id is missing
        }
        serializer = RPiResultInputSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data.get('source_upload_id')) # Phải là None hoặc không có key

    def test_invalid_missing_required_fields(self):
        """Kiểm tra lỗi khi thiếu các trường bắt buộc."""
        data_no_img = {"timestamp": "2025-05-06T10:00:00Z", "insects": self.valid_insects}
        data_no_ts = {"image_base64": self.fake_base64, "insects": self.valid_insects}
        data_no_insects = {"image_base64": self.fake_base64, "timestamp": "2025-05-06T10:00:00Z"}
        s_no_img = RPiResultInputSerializer(data=data_no_img)
        s_no_ts = RPiResultInputSerializer(data=data_no_ts)
        s_no_insects = RPiResultInputSerializer(data=data_no_insects)
        self.assertFalse(s_no_img.is_valid())
        self.assertIn('image_base64', s_no_img.errors)
        self.assertFalse(s_no_ts.is_valid())
        self.assertIn('timestamp', s_no_ts.errors)
        self.assertFalse(s_no_insects.is_valid())
        self.assertIn('insects', s_no_insects.errors)

    def test_invalid_nonexistent_source_upload_id(self):
        """Kiểm tra lỗi khi source_upload_id không tồn tại."""
        data = {
            "image_base64": self.fake_base64,
            "timestamp": "2025-05-06T10:00:00Z",
            "insects": self.valid_insects,
            "source_upload_id": 99999 # ID không tồn tại
        }
        serializer = RPiResultInputSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('source_upload_id', serializer.errors)

    def test_invalid_result_already_exists_for_source_upload_id(self):
        """Kiểm tra lỗi khi kết quả cho source_upload_id đã tồn tại (nếu dùng OneToOne)."""
        data = {
            "image_base64": self.fake_base64,
            "timestamp": "2025-05-06T10:00:00Z",
            "insects": self.valid_insects,
            "source_upload_id": self.upload_with_result_id # ID đã có kết quả
        }
        serializer = RPiResultInputSerializer(data=data)
        # Nếu dùng OneToOne và có validation trong serializer -> False
        # Nếu không có validation trong serializer -> True, lỗi sẽ xảy ra ở tầng DB/View
        # Ở đây serializer có validate nên mong đợi False
        self.assertFalse(serializer.is_valid())
        self.assertIn('source_upload_id', serializer.errors)
        self.assertTrue('đã tồn tại' in serializer.errors['source_upload_id'][0])


# --- Test cho ProcessingResultOutputSerializer (Output) ---
class ProcessingResultOutputSerializerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create(email='outputtest@example.com', password_hash=ph.hash('outpass'))
        cls.upload = UserUpload.objects.create(
            uploaded_by=cls.user,
            file=SimpleUploadedFile('output_orig.gif', b'orig_gif', 'image/gif')
        )
        cls.timestamp = make_aware(datetime(2025, 5, 7, 16, 0, 0))
        cls.insects = [{'name': 'OutputInsect', 'confidence': 0.6}]
        # Kết quả liên kết với upload
        cls.result_linked = ProcessingResult.objects.create(
            source_upload=cls.upload,
            processed_image=SimpleUploadedFile('output_proc.jpg', b'proc_jpg', 'image/jpeg'),
            detection_timestamp=cls.timestamp,
            detected_insects_json=cls.insects
        )
        # Kết quả không liên kết (từ camera)
        cls.result_unlinked = ProcessingResult.objects.create(
            source_upload=None,
            processed_image=SimpleUploadedFile('output_cam.png', b'proc_png', 'image/png'),
            detection_timestamp=make_aware(datetime(2025, 5, 7, 17, 0, 0)),
            detected_insects_json=[{'name': 'CameraOutput'}]
        )
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')

    def test_serialization_linked_result(self):
        """Kiểm tra serialize kết quả có liên kết upload."""
        serializer = ProcessingResultOutputSerializer(instance=self.result_linked, context={'request': self.request})
        data = serializer.data
        expected_keys = {'id', 'source_upload', 'source_upload_details', 'processed_image',
                         'detection_timestamp', 'detected_insects_json', 'received_at'}
        self.assertEqual(set(data.keys()), expected_keys)
        self.assertEqual(data['source_upload'], self.upload.id)
        self.assertIsNotNone(data['source_upload_details'])
        self.assertEqual(data['source_upload_details']['id'], self.upload.id)
        self.assertEqual(data['source_upload_details']['uploaded_by'], self.user.id)
        self.assertTrue(data['processed_image'].endswith('.jpg'))
        self.assertEqual(data['detected_insects_json'], self.insects)

    def test_serialization_unlinked_result(self):
        """Kiểm tra serialize kết quả không có liên kết upload."""
        serializer = ProcessingResultOutputSerializer(instance=self.result_unlinked, context={'request': self.request})
        data = serializer.data
        self.assertIsNone(data['source_upload'])
        self.assertIsNone(data['source_upload_details']) # Vì source_upload là None
        self.assertTrue(data['processed_image'].endswith('.png'))
        self.assertEqual(data['detected_insects_json'], [{'name': 'CameraOutput'}])