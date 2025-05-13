# notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async # Để chạy query DB bất đồng bộ (nếu cần)
from uploads.models import UserUpload # Ví dụ, nếu UploadStatusConsumer cần kiểm tra
from accounts.models import CustomUser # Ví dụ, nếu cần kiểm tra user_type

class UploadStatusConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upload_id = None
        self.user = None
        self.group_name = None
        # print(f"DEBUG (UploadStatusConsumer - __init__): self.channel_layer type: {type(self.channel_layer)}")

    @database_sync_to_async
    def check_upload_permission(self, user_object, upload_id_to_check):
        if not user_object or not hasattr(user_object, 'id'):
            return False
        try:
            upload_instance = UserUpload.objects.select_related('uploaded_by').get(pk=upload_id_to_check)
            if upload_instance.uploaded_by == user_object or (hasattr(user_object, 'is_admin') and user_object.is_admin):
                return True
            return False
        except UserUpload.DoesNotExist:
            return False
        except Exception: # Bắt các lỗi khác
            return False

    async def connect(self):
        # if self.channel_layer is None: # Bạn cần đảm bảo channel_layer được gán đúng
        #     await self.close(code=4002) 
        #     return

        self.upload_id = self.scope['url_route']['kwargs'].get('upload_id')
        self.user = self.scope.get('user')

        user_email_for_log = getattr(self.user, 'email', 'Anonymous')
        # print(f"DEBUG (UploadStatusConsumer - connect): upload_id: {self.upload_id}, User: {user_email_for_log}")

        if not (self.upload_id and self.user and hasattr(self.user, 'id') and self.user.id is not None):
            await self.close(code=4001)
            return
        
        is_allowed = await self.check_upload_permission(self.user, self.upload_id)

        if is_allowed:
            self.group_name = f"upload_{self.upload_id}_status"
            if self.channel_layer: # Kiểm tra trước khi sử dụng
                 await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            # print(f"DEBUG (UploadStatusConsumer - connect): User {user_email_for_log} accepted for upload {self.upload_id}.")
            # await self.send(text_data=json.dumps({'type': 'connection_established', 'message': f'Connected for upload ID: {self.upload_id}'}))
        else:
            # print(f"DEBUG (UploadStatusConsumer - connect): Permission denied for {user_email_for_log} on upload {self.upload_id}.")
            await self.close(code=4004)

    async def disconnect(self, close_code):
        # print(f"DEBUG (UploadStatusConsumer - disconnect): Upload ID {self.upload_id}, Close code: {close_code}")
        if self.group_name and self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_upload_status(self, event): # Tên hàm khớp với type trong group_send
        message_content = event['message']
        # print(f"DEBUG (UploadStatusConsumer - send_upload_status): Sending to client: {message_content}")
        await self.send(text_data=json.dumps(message_content))


# ---- ĐỊNH NGHĨA CLASS LiveFeedConsumer Ở ĐÂY ----
class LiveFeedConsumer(AsyncWebsocketConsumer):
    group_name = "live_camera_feed_viewers" # Tên group chung

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        # print(f"DEBUG ({self.__class__.__name__} - __init__): self.channel_layer type: {type(self.channel_layer)}")

    async def connect(self):
        self.user = self.scope.get('user')
        
        is_admin = False
        if self.user and hasattr(self.user, 'id') and self.user.id is not None:
            # Giả sử CustomUser có property is_admin hoặc bạn kiểm tra user_type
            if hasattr(self.user, 'is_admin') and self.user.is_admin:
                 is_admin = True
            # elif hasattr(self.user, 'user_type') and self.user.user_type == 'ADMIN': # Hoặc kiểm tra trực tiếp
            #     is_admin = True
        
        # print(f"DEBUG (LiveFeedConsumer - connect): User: {getattr(self.user, 'email', 'Anonymous')}, is_admin_check: {is_admin}")

        if is_admin:
            if self.channel_layer is None:
                # print("LiveFeedConsumer (connect): CRITICAL! self.channel_layer is None. Closing.")
                await self.close(code=4002)
                return

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            # print(f"DEBUG (LiveFeedConsumer - connect): Admin {getattr(self.user, 'email', '')} connected to group {self.group_name}")
        else:
            # print("LiveFeedConsumer (connect): Connection rejected. User is not Admin or not authenticated.")
            await self.close(code=4004) # Permission denied

    async def disconnect(self, close_code):
        # print(f"DEBUG (LiveFeedConsumer - disconnect): User {getattr(self.user, 'email', '')} from group {self.group_name}. Code: {close_code}")
        if self.channel_layer:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def send_live_frame(self, event):
        """
        Hàm này được gọi bởi channel_layer.group_send với type="send.live.frame"
        Nó nhận payload (chứa frame ảnh) từ event và gửi xuống client Admin.
        """
        payload_data = event['payload'] 
        # print(f"DEBUG (LiveFeedConsumer - send_live_frame): Relaying frame to {self.channel_name}")
        await self.send(text_data=json.dumps({
            'type': 'live_camera_frame', # Để frontend nhận diện loại message
            'data': payload_data
        }))
# ------------------------------------------
# === THÊM CONSUMER MỚI CHO RASPBERRY PI NHẬN TASK ===
# ===========================================================
class RPiTaskConsumer(AsyncWebsocketConsumer):
    group_name = "rpi_workers_group" # Tên group cố định cho các RPi worker

    async def connect(self):
        # TẠM THỜI CHẤP NHẬN MỌI KẾT NỐI ĐẾN ENDPOINT NÀY
        # Không kiểm tra API Key hay user đặc biệt nào
        # GHI CHÚ: Cần thêm cơ chế xác thực RPi ở đây sau này!
        print(f"DEBUG ({self.__class__.__name__} - connect): Incoming RPi connection attempt...")
        
        if self.channel_layer is None: 
            print(f"DEBUG ({self.__class__.__name__} - connect): CRITICAL! Channel layer is None. Closing.")
            await self.close()
            return

        # Thêm RPi vào group chung
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        print(f"DEBUG ({self.__class__.__name__} - connect): RPi connected (channel: {self.channel_name}) and joined group {self.group_name}. Waiting for tasks.")

    async def disconnect(self, close_code):
        print(f"DEBUG ({self.__class__.__name__} - disconnect): RPi disconnected (channel: {self.channel_name}). Code: {close_code}")
        # Tự động rời khỏi group
        if self.channel_layer:
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def rpi_new_task(self, event):
        """
        Hàm này được gọi khi BE (UserUploadAPIView) gửi message 
        với type='rpi.new.task' vào group 'rpi_workers_group'.
        Nó sẽ lấy thông tin task và gửi xuống cho RPi client đang kết nối.
        """
        task_info = event['message'] # Dữ liệu BE gửi, ví dụ: {'type': 'new_upload', 'upload_id': 133}
        print(f"DEBUG ({self.__class__.__name__} - rpi_new_task): Relaying task to RPi {self.channel_name}: {task_info}")
        try:
            await self.send(text_data=json.dumps({
                'type': 'new_task_assignment', # Loại message để RPi nhận biết
                'data': task_info
            }))
            print(f"DEBUG ({self.__class__.__name__} - rpi_new_task): Task relayed successfully.")
        except Exception as e:
             print(f"DEBUG ({self.__class__.__name__} - rpi_new_task): Error sending task to RPi: {e}")