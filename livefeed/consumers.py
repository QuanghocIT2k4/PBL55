# livefeed/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
# Import model User hoặc permission nếu cần kiểm tra quyền Admin phức tạp hơn
# from accounts.models import CustomUser 

class LiveFeedConsumer(AsyncWebsocketConsumer):
    # Tên group phải khớp với tên được dùng trong ReceiveLiveFrameAPIView
    group_name = "live_camera_feed" 

    async def connect(self):
        self.user = self.scope.get('user') # User từ middleware xác thực WebSocket

        # --- KIỂM TRA QUYỀN ADMIN ---
        is_admin = False
        if self.user and hasattr(self.user, 'id') and self.user.id is not None:
            # Dùng property is_admin nếu có trong CustomUser model
            if hasattr(self.user, 'is_admin') and self.user.is_admin:
                 is_admin = True
            # Hoặc kiểm tra user_type
            # elif hasattr(self.user, 'user_type') and self.user.user_type == 'ADMIN':
            #     is_admin = True

        # print(f"DEBUG (LiveFeedConsumer - connect): User: {getattr(self.user, 'email', 'Anonymous')}, is_admin={is_admin}")

        if is_admin: # Chỉ Admin mới được kết nối để xem
            if self.channel_layer is None: 
                await self.close(code=4002)
                return

            # Thêm Admin client vào group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept() # Chấp nhận kết nối
            # print(f"DEBUG (LiveFeedConsumer - connect): Admin {getattr(self.user, 'email', '')} connected to group {self.group_name}")
        else:
            # print(f"DEBUG (LiveFeedConsumer - connect): REJECTED. Not Admin or not authenticated.")
            await self.close(code=4004) # Permission denied

    async def disconnect(self, close_code):
        # print(f"DEBUG (LiveFeedConsumer - disconnect): User {getattr(self.user, 'email', '')} disconnected. Code: {close_code}")
        # Tự động rời khỏi group
        if self.channel_layer:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_live_frame(self, event):
        """
        Hàm này được gọi khi có message với type='send.live.frame' được gửi đến group.
        Nó sẽ lấy payload (chứa frame base64 và timestamp) và gửi cho client Admin.
        """
        payload_data = event['payload'] 

        # print(f"DEBUG (LiveFeedConsumer - send_live_frame): Relaying frame to {self.channel_name}")
        # Gửi dữ liệu xuống client WebSocket
        await self.send(text_data=json.dumps({
            'type': 'live_feed_frame', # Loại message để frontend nhận diện
            'data': payload_data
        }))