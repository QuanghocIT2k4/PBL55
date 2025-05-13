# stats/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # URL để client kết nối vào nhận cập nhật stats
    path('ws/stats/', consumers.StatsConsumer.as_asgi()),
]