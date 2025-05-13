# results/views.py
import base64
import uuid
import os
import json
import traceback # Để in traceback khi có lỗi
from datetime import date
from django.utils import timezone # Hoặc from datetime import datetime

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.http import Http404

from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

# Import Channels và Async helper
# Đảm bảo channels đã được cài đặt và cấu hình đúng trong settings.py và asgi.py
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    CHANNELS_INSTALLED_SUCCESSFULLY = True
except ImportError:
    print("WARNING: Django Channels is not installed or configured properly. Real-time features will not work.")
    # Định nghĩa hàm giả để code không bị lỗi nếu channels chưa cài
    def get_channel_layer(): return None
    def async_to_sync(func): return func
    CHANNELS_INSTALLED_SUCCESSFULLY = False


# Import từ các app khác
from .models import ProcessingResult
from uploads.models import UserUpload # <<< Import UserUpload để liên kết và cập nhật status
from .serializers import RPiResultInputSerializer, ProcessingResultOutputSerializer
from accounts.permissions import IsAuthenticatedCustom, IsAdminUserType #, HasRPiAPIKey (nếu dùng)
from accounts.models import CustomUser

# Django-filter imports (cho chức năng search)
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProcessingResultFilter # Giả sử bạn đã tạo file filters.py


# --- 1. API ĐỂ RPI GỬI KẾT QUẢ ĐÃ XỬ LÝ (ĐÃ CẬP NHẬT LOGIC GỬI WS CHO STATS) ---
class SaveResultAPIView(views.APIView):
    """
    API endpoint để RPi gửi kết quả xử lý cuối cùng lên server.
    Xử lý cả kết quả từ User Upload và Camera RPi.
    Gửi thông báo WebSocket cho User (trạng thái upload) và cho Dashboard Stats.
    POST: /api/results/save/
    """
    # permission_classes = [HasRPiAPIKey] # <<< NÊN DÙNG KHI BẢO MẬT
    permission_classes = [permissions.AllowAny] # Tạm thời để test (KHÔNG AN TOÀN)

    def post(self, request, *args, **kwargs):
        serializer = RPiResultInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        image_base64 = validated_data['image_base64']
        detection_timestamp_from_rpi = validated_data['timestamp']
        insects_json = validated_data['insects']
        source_upload_id_from_rpi = validated_data.get('source_upload_id')
        # Giả sử RPiResultInputSerializer đã có video_timestamp_sec (nếu bạn đã thêm)
        video_timestamp_sec_from_rpi = validated_data.get('video_timestamp_sec')


        # --- Xử lý ảnh base64 ---
        try:
            if ';base64,' in image_base64:
                img_format, imgstr = image_base64.split(';base64,')
                ext_map = {'jpeg': 'jpg', 'png': 'png', 'gif': 'gif'}
                ext = ext_map.get(img_format.split('/')[-1], 'jpg')
            else:
                imgstr = image_base64
                ext = 'jpg'
            
            today = date.today()
            unique_id_val = uuid.uuid4()
            file_name_val = f"processed_{today.strftime('%Y%m%d')}_{unique_id_val}.{ext}"
            processed_image_data = ContentFile(base64.b64decode(imgstr), name=file_name_val)
        except Exception as e_decode:
            print(f"Error decoding/processing base64 in SaveResultAPIView: {e_decode}")
            traceback.print_exc()
            return Response({'status': 'fail', 'reason': 'Invalid processed image base64', 'details': str(e_decode)}, status=status.HTTP_400_BAD_REQUEST)

        # --- Lấy đối tượng UserUpload nếu ID được cung cấp ---
        user_upload_instance_for_result = None
        if source_upload_id_from_rpi is not None:
            try:
                user_upload_instance_for_result = UserUpload.objects.select_related('uploaded_by').get(pk=source_upload_id_from_rpi)
                print(f"DEBUG (SaveResultAPIView): Found UserUpload ID {source_upload_id_from_rpi} with status {user_upload_instance_for_result.status}")
            except UserUpload.DoesNotExist:
                print(f"ERROR (SaveResultAPIView): UserUpload ID {source_upload_id_from_rpi} not found in DB!")
                return Response({'status': 'fail', 'reason': f'UserUpload with ID={source_upload_id_from_rpi} inconsistency.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- Tạo bản ghi ProcessingResult ---
        try:
            create_kwargs = {
                'source_upload': user_upload_instance_for_result,
                'processed_image': processed_image_data,
                'detection_timestamp': detection_timestamp_from_rpi,
                'detected_insects_json': insects_json
            }
            # Thêm video_timestamp_sec vào nếu bạn đã thêm trường này vào model ProcessingResult
            if hasattr(ProcessingResult(), 'video_timestamp_sec'): # Kiểm tra model có trường đó không
                create_kwargs['video_timestamp_sec'] = video_timestamp_sec_from_rpi

            new_result = ProcessingResult.objects.create(**create_kwargs)
            print(f"DEBUG (SaveResultAPIView): Created ProcessingResult ID {new_result.id}")

            # --- LOGIC GỬI THÔNG BÁO WEBSOCKET CHO USER (TRẠNG THÁI UPLOAD) ---
            if user_upload_instance_for_result and CHANNELS_INSTALLED_SUCCESSFULLY:
                upload_id_to_notify = user_upload_instance_for_result.id
                group_name_to_notify = f"upload_{upload_id_to_notify}_status"
                channel_layer_user = get_channel_layer()

                if channel_layer_user is None:
                    print(f"ERROR (SaveResultAPIView): Channel layer is None! Cannot send WS notification for upload {upload_id_to_notify}.")
                else:
                    processed_image_url_abs = None
                    if new_result.processed_image and hasattr(new_result.processed_image, 'url'):
                        try:
                            if request: processed_image_url_abs = request.build_absolute_uri(new_result.processed_image.url)
                            else: processed_image_url_abs = new_result.processed_image.url
                        except Exception as e_url:
                            print(f"Warning (SaveResultAPIView): Could not build absolute URI: {e_url}")
                            if new_result.processed_image: processed_image_url_abs = new_result.processed_image.url
                    
                    user_status_payload = {
                        "type": "upload_status_update",
                        "status": "completed",
                        "upload_id": upload_id_to_notify,
                        "result_id": new_result.id,
                        "detail": f"File của bạn (ID upload: {upload_id_to_notify}) đã được xử lý.",
                        "processed_image_url": processed_image_url_abs
                    }
                    try:
                        async_to_sync(channel_layer_user.group_send)(
                            group_name_to_notify,
                            {"type": "send.upload.status", "message": user_status_payload}
                        )
                        print(f"DEBUG (SaveResultAPIView): Sent WebSocket user status for upload_id: {upload_id_to_notify}")
                    except Exception as ws_send_error_user:
                        print(f"ERROR (SaveResultAPIView): Could not send WebSocket user status for upload {upload_id_to_notify}: {ws_send_error_user}")
                
                # Cập nhật status của UserUpload
                if user_upload_instance_for_result.status != UserUpload.STATUS_COMPLETED:
                    user_upload_instance_for_result.status = UserUpload.STATUS_COMPLETED
                    update_fields = ['status']
                    if hasattr(user_upload_instance_for_result, 'updated_at'):
                        user_upload_instance_for_result.updated_at = timezone.now()
                        update_fields.append('updated_at')
                    user_upload_instance_for_result.save(update_fields=update_fields)
                    print(f"DEBUG (SaveResultAPIView): UserUpload ID {upload_id_to_notify} status updated to {UserUpload.STATUS_COMPLETED}.")
            # -----------------------------------------------------------------

            # --- LOGIC GỬI THÔNG BÁO CẬP NHẬT STATS QUA WEBSOCKET ---
            if CHANNELS_INSTALLED_SUCCESSFULLY:
                stats_channel_layer = get_channel_layer()
                if stats_channel_layer is None:
                     print(f"ERROR (SaveResultAPIView): Channel layer is None! Cannot send stats update for result ID {new_result.id}.")
                else:
                    stats_update_payload = {
                        'event_type': 'new_insect_detection',
                        'result_id': new_result.id,
                        'detected_insects': new_result.detected_insects_json,
                        'detection_date': new_result.detection_timestamp.strftime('%Y-%m-%d'),
                        'source_type': 'user_upload' if new_result.source_upload else 'camera_feed'
                    }
                    stats_group_name = "dashboard_stats_updates"
                    try:
                        async_to_sync(stats_channel_layer.group_send)(
                            stats_group_name,
                            {"type": "send.stats.update", "message": stats_update_payload}
                        )
                        print(f"DEBUG (SaveResultAPIView): Sent stats update notification to group {stats_group_name} for result ID {new_result.id}")
                    except Exception as stats_send_error:
                        print(f"ERROR (SaveResultAPIView): Could not send stats update notification for result ID {new_result.id}: {stats_send_error}")
                        traceback.print_exc()
            # -----------------------------------------------------------
            
            output_serializer = ProcessingResultOutputSerializer(new_result, context={'request': request})
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"Error creating ProcessingResult or sending WS in SaveResultAPIView: {e}")
            traceback.print_exc()
            if user_upload_instance_for_result:
                if user_upload_instance_for_result.status != UserUpload.STATUS_FAILED:
                    user_upload_instance_for_result.status = UserUpload.STATUS_FAILED
                    update_fields = ['status']
                    if hasattr(user_upload_instance_for_result, 'updated_at'):
                        user_upload_instance_for_result.updated_at = timezone.now()
                        update_fields.append('updated_at')
                    user_upload_instance_for_result.save(update_fields=update_fields)
                    print(f"DEBUG (SaveResultAPIView): UserUpload ID {user_upload_instance_for_result.id} status updated to {UserUpload.STATUS_FAILED} due to error.")
            return Response({'status': 'fail', 'reason': 'Could not save processing result', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 2. API ĐỂ FRONTEND LẤY KẾT QUẢ THEO UPLOAD ID ---
class GetResultByUploadAPIView(generics.RetrieveAPIView):
    """
    API endpoint để Frontend lấy kết quả xử lý dựa trên ID của UserUpload gốc.
    Kiểm tra quyền sở hữu của người dùng.
    GET: /api/results/by-upload/{upload_id}/
    """
    queryset = ProcessingResult.objects.select_related('source_upload__uploaded_by').all()
    serializer_class = ProcessingResultOutputSerializer
    permission_classes = [IsAuthenticatedCustom] # Yêu cầu user đăng nhập
    lookup_field = 'source_upload_id' # Tìm ProcessingResult dựa trên FK source_upload_id
    lookup_url_kwarg = 'upload_id'    # Lấy giá trị ID từ tham số {upload_id} trong URL

    def get_object(self):
        """Ghi đè để kiểm tra quyền sở hữu của user hoặc nếu user là Admin."""
        try:
            obj = super().get_object()
        except Http404:
            raise Http404("Không tìm thấy kết quả xử lý cho lần upload này.")

        # Kiểm tra user hiện tại có phải là người đã upload file gốc không HOẶC có phải Admin không
        current_user = self.request.user
        if not obj.source_upload:
             # Trường hợp này chỉ Admin mới xem được (nếu có API riêng)
             # hoặc lỗi logic nếu user thường gọi URL này mà không có source_upload
            raise Http404("Kết quả này không phải từ file upload.")

        is_owner = obj.source_upload.uploaded_by == current_user
        is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin

        if not (is_owner or is_admin):
            raise PermissionDenied("Bạn không có quyền xem kết quả này.")

        return obj


# --- 3. API ĐỂ ADMIN LẤY KẾT QUẢ TỪ CAMERA RPI ---
class DeviceFeedAPIView(generics.ListAPIView):
    """
    API endpoint để Frontend (chỉ Admin) lấy danh sách kết quả xử lý từ Camera RPi
    (những bản ghi có source_upload là NULL). Có thể thêm filter ngày tháng.
    GET: /api/results/device-feed/?start_date=...&end_date=...
    """
    queryset = ProcessingResult.objects.filter(source_upload__isnull=True).order_by('-received_at', '-detection_timestamp')
    serializer_class = ProcessingResultOutputSerializer
    permission_classes = [IsAdminUserType] # <<< CHỈ ADMIN ĐƯỢC TRUY CẬP
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'detection_timestamp': ['date__gte', 'date__lte'] # Cho phép lọc ?detection_timestamp__date__gte=YYYY-MM-DD
    }
    # (Tùy chọn) Thêm phân trang
    # pagination_class = PageNumberPagination
    # pagination_class.page_size = 20


# --- 4. API ĐỂ TÌM KIẾM/LỌC KẾT QUẢ XỬ LÝ ---
class ProcessingResultSearchView(generics.ListAPIView):
    """
    API endpoint để tìm kiếm và lọc các kết quả xử lý.
    GET /api/results/search/?start_date=...&end_date=...&insect_name=...
    """
    serializer_class = ProcessingResultOutputSerializer
    permission_classes = [IsAuthenticatedCustom] # Yêu cầu đăng nhập
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProcessingResultFilter # FilterSet định nghĩa trong results/filters.py

    def get_queryset(self):
        """
        Xác định queryset ban đầu dựa trên loại người dùng.
        """
        user = self.request.user
        if not user or not hasattr(user, 'id'): # Kiểm tra user hợp lệ
            return ProcessingResult.objects.none() 

        if hasattr(user, 'is_admin') and user.is_admin:
            # Admin: Lấy tất cả kết quả
            print(f"DEBUG (ProcessingResultSearchView): Admin Query")
            return ProcessingResult.objects.select_related('source_upload__uploaded_by').all().order_by('-received_at')
        else: # Mặc định là user thường nếu không phải admin và đã xác thực
            # User thường: Chỉ lấy kết quả từ file họ đã upload
             print(f"DEBUG (ProcessingResultSearchView): Regular User Query for user ID {user.id}")
             return ProcessingResult.objects.select_related('source_upload__uploaded_by').filter(source_upload__uploaded_by=user).order_by('-received_at')