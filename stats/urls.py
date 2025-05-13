# stats/urls.py
from django.urls import path
from . import views # Import views từ app stats

urlpatterns = [
    # Định nghĩa URL cho API thống kê tần suất
    path('frequency/', views.FrequencyStatsView.as_view(), name='stats-frequency'),
    # Thêm các URL cho các loại thống kê khác sau này nếu cần
]