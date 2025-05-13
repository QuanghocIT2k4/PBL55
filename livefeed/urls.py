# livefeed/urls.py
from django.urls import path
from .views import ReceiveLiveFrameAPIView

app_name = 'livefeed'

urlpatterns = [
    # URL để RPi gửi frame lên, ví dụ: /api/livefeed/send-frame/
    path('send-frame/', ReceiveLiveFrameAPIView.as_view(), name='send_live_frame'),
]