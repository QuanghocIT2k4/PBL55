# livefeed/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # URL để Admin client kết nối vào xem live, ví dụ: ws://server/ws/livefeed/view/
    path('ws/livefeed/view/', consumers.LiveFeedConsumer.as_asgi()), 
]