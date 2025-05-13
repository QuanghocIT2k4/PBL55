# stats/tests.py
import json
from datetime import date, datetime, timedelta
from django.urls import reverse
from django.utils.timezone import make_aware
from rest_framework import status
from rest_framework.test import APITestCase

# Import models từ các app khác
from accounts.models import CustomUser
from results.models import ProcessingResult, UserUpload # Cần cả hai

# Import thư viện hash
from argon2 import PasswordHasher
ph = PasswordHasher()

class FrequencyStatsViewTest(APITestCase):
    """Test cho API thống kê tần suất /api/stats/frequency/."""

    @classmethod
    def setUpTestData(cls):
        # Tạo user để xác thực API
        cls.user = CustomUser.objects.create(
            email='statsuser@example.com',
            password_hash=ph.hash('statspass'),
            is_active=True
        )
        # Tạo dữ liệu ProcessingResult mẫu
        # Ngày 1
        ts1 = make_aware(datetime(2025, 5, 1, 10, 0, 0))
        insects1 = [{'name': 'MuoiVang', 'confidence': 0.9}, {'name': 'BoCanhCam', 'confidence': 0.8}]
        ProcessingResult.objects.create(detection_timestamp=ts1, detected_insects_json=insects1)
        # Cùng ngày 1, kết quả khác, có trùng lặp côn trùng
        ts1_later = make_aware(datetime(2025, 5, 1, 14, 0, 0))
        insects1_later = [{'name': 'MuoiVang', 'confidence': 0.95}] # Chỉ có MuoiVang
        ProcessingResult.objects.create(detection_timestamp=ts1_later, detected_insects_json=insects1_later)
        # Ngày 2
        ts2 = make_aware(datetime(2025, 5, 2, 9, 0, 0))
        insects2 = [{'name': 'BoCanhCam', 'confidence': 0.7}]
        ProcessingResult.objects.create(detection_timestamp=ts2, detected_insects_json=insects2)
        # Ngày 3
        ts3 = make_aware(datetime(2025, 5, 3, 11, 0, 0))
        insects3 = [{'name': 'SauXanh', 'confidence': 0.99}]
        ProcessingResult.objects.create(detection_timestamp=ts3, detected_insects_json=insects3)

        cls.url = reverse('stats-frequency') # Lấy URL từ tên 'stats-frequency' trong stats/urls.py

    def _get_token(self):
        """Helper lấy token."""
        response = self.client.post(reverse('accounts:user_login'), {'email': 'statsuser@example.com', 'password': 'statspass'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['access']

    def setUp(self):
        """Lấy token trước mỗi test."""
        self.token = self._get_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_frequency_stats_success(self):
        """Kiểm tra lấy thống kê thành công và dữ liệu đúng."""
        # Test cho khoảng thời gian chứa tất cả dữ liệu mẫu
        start_date = '2025-05-01'
        end_date = '2025-05-03'
        response = self.client.get(self.url, {'start_date': start_date, 'end_date': end_date})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        # Kiểm tra cấu trúc cơ bản
        self.assertIn('labels', data)
        self.assertIn('datasets', data)

        # Kiểm tra labels (các ngày trong khoảng)
        expected_labels = ['2025-05-01', '2025-05-02', '2025-05-03']
        self.assertEqual(data['labels'], expected_labels)

        # Kiểm tra datasets
        self.assertEqual(len(data['datasets']), 3) # Phải có 3 côn trùng: BoCanhCam, MuoiVang, SauXanh

        # Tìm dataset cho từng côn trùng (thứ tự có thể khác nhau tùy sắp xếp)
        muoi_vang_data = next((ds for ds in data['datasets'] if ds['label'] == 'MuoiVang'), None)
        bo_canh_cam_data = next((ds for ds in data['datasets'] if ds['label'] == 'BoCanhCam'), None)
        sau_xanh_data = next((ds for ds in data['datasets'] if ds['label'] == 'SauXanh'), None)

        self.assertIsNotNone(muoi_vang_data)
        self.assertIsNotNone(bo_canh_cam_data)
        self.assertIsNotNone(sau_xanh_data)

        # Kiểm tra dữ liệu điểm (1 nếu xuất hiện, 0 nếu không, chỉ 1 lần/ngày)
        # Ngày 1: MuoiVang(1), BoCanhCam(1), SauXanh(0)
        # Ngày 2: MuoiVang(0), BoCanhCam(1), SauXanh(0)
        # Ngày 3: MuoiVang(0), BoCanhCam(0), SauXanh(1)
        self.assertEqual(muoi_vang_data['data'], [1, 0, 0])
        self.assertEqual(bo_canh_cam_data['data'], [1, 1, 0])
        self.assertEqual(sau_xanh_data['data'], [0, 0, 1])

    def test_get_frequency_stats_no_data_in_range(self):
        """Kiểm tra khi không có dữ liệu trong khoảng thời gian."""
        start_date = '2025-06-01'
        end_date = '2025-06-05'
        response = self.client.get(self.url, {'start_date': start_date, 'end_date': end_date})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        expected_labels = ['2025-06-01', '2025-06-02', '2025-06-03', '2025-06-04', '2025-06-05']
        self.assertEqual(data['labels'], expected_labels)
        self.assertEqual(len(data['datasets']), 0) # Không có dataset nào

    def test_get_frequency_stats_invalid_date_range(self):
        """Kiểm tra lỗi khi ngày bắt đầu sau ngày kết thúc."""
        start_date = '2025-05-03'
        end_date = '2025-05-01'
        response = self.client.get(self.url, {'start_date': start_date, 'end_date': end_date})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_get_frequency_stats_invalid_date_format(self):
        """Kiểm tra lỗi khi định dạng ngày sai."""
        start_date = '01-05-2025' # Sai định dạng
        end_date = '2025-05-03'
        response = self.client.get(self.url, {'start_date': start_date, 'end_date': end_date})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_get_frequency_stats_unauthenticated(self):
        """Kiểm tra lỗi khi chưa đăng nhập."""
        self.client.credentials() # Xóa token
        response = self.client.get(self.url, {'start_date': '2025-05-01', 'end_date': '2025-05-01'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)