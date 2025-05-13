# livefeed/views.py
from django.utils import timezone
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

# Import Channels và Async helper
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    CHANNELS_INSTALLED_SUCCESSFULLY = True
except ImportError:
    print("WARNING: Django Channels is not installed or configured properly. Livefeed features might not work.")
    get_channel_layer = lambda: None # Hàm giả
    async_to_sync = lambda func: func # Hàm giả
    CHANNELS_INSTALLED_SUCCESSFULLY = False

import json
import traceback

# Tùy chọn: Import permission nếu bạn làm bảo mật API Key
# from accounts.permissions import HasRPiAPIKey 

class ReceiveLiveFrameAPIView(APIView):
    """
    API endpoint để RPi gửi từng frame ảnh trực tiếp lên server.
    Server sẽ nhận frame này và chuyển tiếp qua WebSocket cho các Admin đang xem.
    POST: /api/livefeed/send-frame/  (Ví dụ URL)
    (API này CẦN được bảo mật bằng API Key trong thực tế)
    """
    # permission_classes = [HasRPiAPIKey] # <<< Nên dùng permission này khi đã tạo
    permission_classes = [permissions.AllowAny] # Tạm thời cho phép mọi request để test

    def post(self, request, *args, **kwargs):
        frame_base64_datauri = request.data.get('frame_base64') 
        frame_timestamp = request.data.get('timestamp', datetime.utcnow().isoformat() + "Z") 

        if not frame_base64_datauri:
            return Response({"error": "Missing 'frame_base64' field in request body."}, status=status.HTTP_400_BAD_REQUEST)

        # Chuẩn bị payload để gửi qua WebSocket
        websocket_payload = {
            'image_base64': frame_base64_datauri, 
            'timestamp': frame_timestamp,
        }

        channel_layer = get_channel_layer() 
        if channel_layer is None: 
            print("CRITICAL ERROR (ReceiveLiveFrameAPIView): Channel layer is None!")
            return Response({"error": "Lỗi hệ thống: Channel layer không khả dụng."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Tên group mà các Admin client sẽ lắng nghe
        admin_live_feed_group = "live_camera_feed" # Đặt tên group nhất quán

        try:
            async_to_sync(channel_layer.group_send)(
                admin_live_feed_group, 
                {
                    "type": "send.live.frame", # Hàm xử lý trong LiveFeedConsumer (đổi dấu . thành _)
                    "payload": websocket_payload # Dữ liệu gửi đi
                }
            )
            # print(f"DEBUG (ReceiveLiveFrameAPIView): Relayed frame to group '{admin_live_feed_group}'")
            return Response({"status": "frame_relayed"}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"ERROR (ReceiveLiveFrameAPIView): Could not send frame to channel group '{admin_live_feed_group}': {e}")
            traceback.print_exc() 
            return Response({"error": "Lỗi khi chuyển tiếp frame qua WebSocket."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)