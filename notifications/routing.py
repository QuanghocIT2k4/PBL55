# notifications/routing.py
from django.urls import path, re_path # re_path nếu bạn dùng regular expression phức tạp
from . import consumers

websocket_urlpatterns = [
    path('ws/upload-status/<int:upload_id>/', consumers.UploadStatusConsumer.as_asgi()),
    
    # Đảm bảo dòng này trỏ đúng đến class LiveFeedConsumer đã được định nghĩa
    # trong file notifications/consumers.py
    re_path(r'^ws/camera/view/$', consumers.LiveFeedConsumer.as_asgi()), 
    # Ký tự ^ ở đầu và $ ở cuối để khớp chính xác chuỗi (best practice cho re_path)

    # path('ws/stats/', consumers.StatsConsumer.as_asgi()), # Khi bạn làm chức năng Stats Realtime
    
    
    # --- THÊM ĐỊNH TUYẾN MỚI CHO RPI ---
    # URL để RPi kết nối vào lắng nghe task mới
    path('ws/rpi/listen-tasks/', consumers.RPiTaskConsumer.as_asgi()),
    # ---------------------------------
]