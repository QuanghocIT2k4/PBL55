# main_config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Import middleware xác thực token tùy chỉnh của bạn
from accounts.middleware import TokenAuthMiddleware 

# Import các file routing.py từ các app có chứa WebSocket consumers
import notifications.routing  # Cho UploadStatusConsumer
import livefeed.routing       # Cho LiveFeedConsumer (app mới)
import stats.routing        # Thêm dòng này nếu bạn tạo consumer cho stats

# Chỉ định file settings cho Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_config.settings')

# Lấy ASGI application mặc định của Django cho các request HTTP
django_asgi_app = get_asgi_application()

# Định nghĩa cấu trúc application ASGI chính
application = ProtocolTypeRouter({
    # Xử lý các request HTTP thông thường bằng Django
    "http": django_asgi_app,

    # Xử lý các kết nối WebSocket
    "websocket": TokenAuthMiddleware(  # Bước 1: Middleware này xử lý token từ query param, gán user vào scope
        AuthMiddlewareStack(        # Bước 2: Middleware này xử lý session/cookie (nếu có) và các tác vụ auth khác
            URLRouter(              # Bước 3: Định tuyến dựa trên URL của WebSocket
                
                # Liệt kê và kết hợp các websocket_urlpatterns từ các app khác nhau
                # Dùng dấu + để nối các list URL patterns lại với nhau
                
                notifications.routing.websocket_urlpatterns +  # Các URL trong notifications/routing.py
                livefeed.routing.websocket_urlpatterns + 
                stats.routing.websocket_urlpatterns        # Thêm dòng này nếu bạn có app stats với WebSocket
                
            )
        )
    ),
})