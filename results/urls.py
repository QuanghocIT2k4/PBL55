# results/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Endpoint cho RPi gửi kết quả xử lý lên
    path('save/', views.SaveResultAPIView.as_view(), name='save-processing-result'),

    # Endpoint cho Frontend lấy kết quả theo ID upload gốc
    path('by-upload/<int:upload_id>/', views.GetResultByUploadAPIView.as_view(), name='get-result-by-upload'),

    # Endpoint cho Frontend lấy danh sách kết quả từ camera RPi
    path('device-feed/', views.DeviceFeedAPIView.as_view(), name='get-device-feed'),
    
    path('search/', views.ProcessingResultSearchView.as_view(), name='search_results'),
]