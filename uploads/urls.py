# uploads/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Endpoint cho User upload file (dùng POST)
    path('upload/', views.UserUploadAPIView.as_view(), name='user-upload'),

    # Endpoint cho RPi/Backend lấy file theo ID (dùng GET)
    # <int:upload_id> là tham số động, sẽ được truyền vào hàm get của View
    path('get-media/<int:upload_id>/', views.GetMediaForProcessingAPIView.as_view(), name='get-media-for-processing'),
]