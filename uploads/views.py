# uploads/views.py
import base64
import os
import traceback # Để log lỗi chi tiết
import json      # Để tạo message cho WebSocket
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone # Import timezone nếu bạn cập nhật updated_at
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import ValidationError, PermissionDenied

# Import Channels (để gửi thông báo trigger RPi)
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    CHANNELS_INSTALLED_SUCCESSFULLY = True
except ImportError:
    print("WARNING: Django Channels is not installed or configured properly. RPi trigger via WebSocket will not work.")
    get_channel_layer = lambda: None
    async_to_sync = lambda func: func
    CHANNELS_INSTALLED_SUCCESSFULLY = False

# Import từ các app khác
from .models import UserUpload
from .serializers import UserUploadSerializer # Serializer để trả về thông tin
from accounts.models import CustomUser # Import CustomUser để kiểm tra type nếu cần
# Import các permission cần thiết từ accounts/permissions.py
from accounts.permissions import IsAuthenticatedCustom, IsRegularUserType

# --- 1. API ĐỂ USER THƯỜNG UPLOAD FILE (ĐÃ THÊM LOGIC TRIGGER RPI) ---
class UserUploadAPIView(generics.CreateAPIView):
    """
    API endpoint để User THƯỜNG đã đăng nhập tải lên file ảnh hoặc video.
    POST: /api/uploads/upload/
    Sau khi lưu file thành công, sẽ gửi thông báo task mới cho RPi qua WebSocket.
    """
    queryset = UserUpload.objects.all()
    serializer_class = UserUploadSerializer
    permission_classes = [IsAuthenticatedCustom, IsRegularUserType] # Đã thêm IsRegularUserType
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def perform_create(self, serializer):
        """
        Lưu file, gán người dùng, và gửi thông báo task mới cho RPi qua WebSocket.
        """
        current_user = self.request.user
        if not isinstance(current_user, CustomUser) or not current_user.is_regular_user:
            print(f"ERROR in perform_create: User {current_user} is not a valid regular user.")
            raise PermissionDenied("Lỗi quyền không mong đợi.")

        file_obj = self.request.FILES.get('file')
        if not file_obj:
            raise ValidationError({"file": ["Không tìm thấy trường 'file' trong dữ liệu form-data."]})

        # (Optional) File validation here

        try:
            # Lưu UserUpload, status mặc định là 'pending' (đã định nghĩa trong model)
            instance = serializer.save(uploaded_by=current_user, file=file_obj)
            print(f"DEBUG (UserUploadAPIView): File uploaded by {current_user.email}, ID: {instance.id}, Initial Status: {instance.status}")

            # ---- TRIGGER GỬI TASK CHO RPI QUA WEBSOCKET ----
            if CHANNELS_INSTALLED_SUCCESSFULLY:
                channel_layer = get_channel_layer()
                if channel_layer is None:
                     print(f"ERROR (UserUploadAPIView): Channel layer is None! Cannot send task notification for upload {instance.id}.")
                else:
                     rpi_group_name = "rpi_workers_group" # Group RPi lắng nghe
                     task_message = {
                         "type": "new_upload", # Loại task để RPi biết
                         "upload_id": instance.id
                         # Có thể thêm các thông tin khác nếu RPi cần
                     }
                     try:
                         # Gửi message vào group của RPi
                         async_to_sync(channel_layer.group_send)(
                             rpi_group_name,
                             {
                                 "type": "rpi.new.task", # Gọi hàm rpi_new_task trong RPiTaskConsumer
                                 "message": task_message
                             }
                         )
                         print(f"DEBUG (UserUploadAPIView): Sent task notification for upload {instance.id} to group {rpi_group_name}")

                         # Cập nhật status thành 'assigned' sau khi gửi thông báo thành công
                         instance.status = UserUpload.STATUS_ASSIGNED # Đảm bảo STATUS_ASSIGNED định nghĩa trong model
                         if hasattr(instance, 'updated_at'):
                             instance.updated_at = timezone.now() # Cần import timezone
                             instance.save(update_fields=['status', 'updated_at'])
                         else:
                              instance.save(update_fields=['status'])
                         print(f"DEBUG (UserUploadAPIView): UserUpload ID {instance.id} status updated to {instance.status}")

                     except Exception as ws_send_error:
                         print(f"ERROR (UserUploadAPIView): Could not send task notification for upload {instance.id}: {ws_send_error}")
                         traceback.print_exc()
                         # Giữ status là 'pending' nếu gửi task thất bại
                         instance.status = UserUpload.STATUS_PENDING
                         instance.save(update_fields=['status'])
                         print(f"WARNING (UserUploadAPIView): UserUpload ID {instance.id} status kept as pending due to WS send error.")
            # ---------------------------------------------

        except Exception as e:
            print(f"Error saving UserUpload for user {current_user.id}: {e}")
            traceback.print_exc()
            raise

# --- 2. API ĐỂ LẤY FILE MEDIA ĐÃ UPLOAD (CHO RPI/BACKEND - GIỮ NGUYÊN AllowAny) ---
class GetMediaForProcessingAPIView(APIView):
    """
    API endpoint để lấy nội dung file (ảnh/video) đã được user upload
    dưới dạng data URI (base64 kèm mime type), dựa trên ID của bản ghi UserUpload.
    GET: /api/uploads/get-media/{upload_id}/
    (Tạm thời không yêu cầu xác thực RPi Key theo yêu cầu)
    """
    permission_classes = [permissions.AllowAny] # <<< GIỮ AllowAny

    def get(self, request, upload_id, *args, **kwargs):
        """Xử lý request GET để lấy và mã hóa file."""
        upload = get_object_or_404(UserUpload, pk=upload_id)

        if not upload.file or not hasattr(upload.file, 'storage') or not upload.file.storage.exists(upload.file.name):
            return Response({"detail": "File không tồn tại trên hệ thống lưu trữ."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with upload.file.open('rb') as file_content:
                file_bytes = file_content.read()

            base64_encoded_data = base64.b64encode(file_bytes)
            base64_string = base64_encoded_data.decode('utf-8')

            file_name = os.path.basename(upload.file.name)
            file_ext = file_name.split('.')[-1].lower()
            mime_map = {
                'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
                'gif': 'image/gif', 'mp4': 'video/mp4', 'mov': 'video/quicktime',
                'avi': 'video/x-msvideo',
            }
            mime_type = mime_map.get(file_ext, 'application/octet-stream')

            data_uri = f"data:{mime_type};base64,{base64_string}"

            response_data = {
                "upload_id": upload.id,
                "original_filename": file_name,
                "upload_time": upload.upload_time,
                "mime_type": mime_type,
                "media_base64": data_uri,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except FileNotFoundError:
             print(f"Error: File not found on disk for ID {upload_id} (Path: {upload.file.name})")
             return Response({"detail": "File không tìm thấy trên hệ thống lưu trữ (disk error)."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error reading/encoding file ID {upload_id} (Path: {upload.file.name}): {e}")
            traceback.print_exc()
            return Response({"detail": "Lỗi máy chủ khi xử lý file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
