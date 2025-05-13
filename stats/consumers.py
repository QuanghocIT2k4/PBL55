# stats/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
# Import permission và model User nếu bạn muốn kiểm tra quyền truy cập phức tạp hơn
# (hiện tại, chỉ cần user đã đăng nhập)

class StatsConsumer(AsyncWebsocketConsumer):
    group_name = "dashboard_stats_updates" # Tên group chung cho tất cả client xem dashboard

    async def connect(self):
        self.user = self.scope.get('user') # User đã được middleware xác thực

        # Yêu cầu người dùng phải đăng nhập để xem stats real-time
        is_authenticated = bool(self.user and getattr(self.user, 'id', None) is not None) 
        user_email_for_log = getattr(self.user, 'email', 'Anonymous')

        print(f"DEBUG (StatsConsumer - connect): User attempting connect: {user_email_for_log}, authenticated: {is_authenticated}")

        if is_authenticated:
            if self.channel_layer is None: 
                print(f"DEBUG ({self.__class__.__name__} - connect): CRITICAL! Channel layer is None. Closing connection.")
                await self.close(code=4002) # Mã lỗi tùy chọn
                return

            # Thêm client này vào group chung
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name # ID duy nhất của kết nối WebSocket này
            )
            await self.accept() # Chấp nhận kết nối WebSocket
            print(f"DEBUG (StatsConsumer - connect): User {user_email_for_log} connected to group '{self.group_name}' for real-time stats.")

            # (Tùy chọn) Bạn có thể gửi dữ liệu thống kê ban đầu ngay khi client kết nối
            # await self.send_initial_stats_data()
        else:
            print(f"DEBUG (StatsConsumer - connect): Connection REJECTED. User not authenticated.")
            await self.close()

    async def disconnect(self, close_code):
        user_email_for_log = getattr(self.user, 'email', 'Anonymous')
        print(f"DEBUG (StatsConsumer - disconnect): User {user_email_for_log} disconnected from group '{self.group_name}'. Code: {close_code}")
        if self.channel_layer: # Luôn kiểm tra trước khi dùng
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_stats_update(self, event):
        """
        Hàm này được gọi khi Backend (ví dụ: SaveResultAPIView) gửi một message 
        với type='send.stats.update' vào group 'dashboard_stats_updates'.
        Nó sẽ lấy payload (dữ liệu stats mới) và gửi xuống client WebSocket.
        """
        stats_data_payload = event['message'] # Dữ liệu thống kê mới từ BE

        print(f"DEBUG (StatsConsumer - send_stats_update): Relaying stats update to client {self.channel_name}: {str(stats_data_payload)[:200]}...") # Log một phần dữ liệu

        try:
            # Gửi dữ liệu xuống client WebSocket
            await self.send(text_data=json.dumps({
                'type': 'stats_dashboard_update', # Một type rõ ràng để Frontend nhận biết
                'data': stats_data_payload
            }))
        except Exception as e:
            print(f"ERROR (StatsConsumer - send_stats_update): Could not send stats update to client {self.channel_name}: {e}")

    # (Tùy chọn) Hàm để gửi dữ liệu thống kê ban đầu
    # async def send_initial_stats_data(self):
    #     # Tại đây, bạn có thể gọi logic tương tự như trong FrequencyStatsView
    #     # để lấy dữ liệu thống kê hiện tại (ví dụ cho 7 ngày gần nhất)
    #     # và gửi cho client vừa kết nối.
    #     print(f"DEBUG (StatsConsumer - send_initial_stats_data): Sending initial stats to {self.channel_name}")
    #     # Ví dụ dữ liệu giả:
    #     initial_data = {"message": "Initial stats data would go here."} 
    #     await self.send(text_data=json.dumps({'type': 'initial_stats_data', 'data': initial_data}))