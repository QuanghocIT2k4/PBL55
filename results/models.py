# results/models.py
from django.db import models
import uuid
import os
from datetime import date

# Import các model liên quan từ app khác
from uploads.models import UserUpload # Model chứa file gốc do user upload
# from accounts.models import CustomUser # Có thể cần nếu muốn liên kết trực tiếp người xử lý

def get_processed_image_path(instance, filename):
    """
    Tạo đường dẫn lưu file ảnh ĐÃ XỬ LÝ, phân biệt nguồn gốc.
    instance: Đối tượng ProcessingResult đang được lưu.
    filename: Tên file gốc (thường là tên mà RPi gửi lên hoặc tên được tạo từ base64).
    """
    # Tách phần mở rộng file (extension)
    # Đảm bảo filename không rỗng và có dấu chấm trước khi split
    name_part, ext_part = os.path.splitext(filename)
    ext = ext_part[1:] if ext_part else 'jpg' # Lấy phần mở rộng không có dấu chấm, mặc định là jpg

    # Tạo thư mục con theo năm/tháng/ngày để dễ quản lý
    today = date.today()
    year = today.strftime("%Y")
    month = today.strftime("%m")
    day = today.strftime("%d")

    # Tạo tên file duy nhất
    unique_id = uuid.uuid4()
    new_filename = f"processed_{year}{month}{day}_{unique_id}.{ext}"

    # Xác định thư mục con dựa trên nguồn gốc
    if instance.source_upload_id is not None: # Kiểm tra trực tiếp FK ID để tránh query không cần thiết nếu instance chưa lưu
        # Hoặc bạn có thể dùng instance.source_upload nếu bạn chắc chắn nó đã được gán
        # và không ngại một query tiềm năng (nếu chưa được select_related/prefetch_related)
        source_folder = 'user_uploads_processed'
        # Tùy chọn: thêm ID của user hoặc upload gốc vào đường dẫn
        # path_prefix = f'user_{instance.source_upload.uploaded_by_id}/upload_{instance.source_upload_id}'
        # return os.path.join('processed_results', source_folder, path_prefix, year, month, day, new_filename)
    else:
        source_folder = 'camera_captures_processed'

    return os.path.join('processed_results', source_folder, year, month, day, new_filename)

class ProcessingResult(models.Model):
    """
    Lưu trữ kết quả xử lý ảnh/video từ RPi,
    có thể liên kết với file upload gốc của người dùng.
    """
    # --- Liên kết với nguồn gốc (Quan trọng) ---
    source_upload = models.OneToOneField(
        UserUpload,
        on_delete=models.SET_NULL, # Nếu xóa file upload gốc, giữ lại kết quả nhưng mất liên kết
        # hoặc models.CASCADE: Nếu xóa file upload gốc thì xóa luôn kết quả này
        null=True,          # Cho phép NULL (nghĩa là kết quả này từ camera RPi trực tiếp)
        blank=True,         # Cho phép để trống trong form (nếu dùng Django Forms/Admin)
        related_name='processing_result', # Tên để truy cập ngược từ UserUpload instance
                                        # Ví dụ: user_upload_obj.processing_result
        verbose_name="File Upload Gốc"
    )

    # --- Thông tin kết quả xử lý ---
    processed_image = models.ImageField(
        upload_to=get_processed_image_path, # <<< Sử dụng hàm đã cập nhật
        verbose_name="Ảnh Đã Xử Lý"
    )
    detection_timestamp = models.DateTimeField(
        # Thời gian do RPi ghi nhận khi xử lý xong, hoặc thời gian chụp ảnh gốc
        db_index=True, # Thường dùng để lọc/sắp xếp
        verbose_name="Thời điểm Phát hiện (từ RPi)"
    )
    detected_insects_json = models.JSONField(
        # Lưu danh sách côn trùng dưới dạng JSON để linh hoạt
        # Ví dụ: [{"name": "muoi_vang", "confidence": 0.9, "bbox": [x1,y1,x2,y2]}, ...]
        # Hoặc chỉ lưu: [{"name": "muoi_vang", "confidence": 0.9}, ...]
        verbose_name="Danh sách Côn trùng Phát hiện (JSON)"
    )

    # --- Thông tin Meta ---
    received_at = models.DateTimeField(
        auto_now_add=True, # Thời điểm Server nhận được kết quả này
        verbose_name="Thời điểm Server Nhận"
    )
    # (Tùy chọn) Thêm các trường khác nếu cần:
    # processing_time_ms = models.IntegerField(null=True, blank=True, verbose_name="Thời gian xử lý (ms)")
    # rpi_device_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="ID Thiết bị RPi")
    # notes = models.TextField(blank=True, null=True, verbose_name="Ghi chú")

    class Meta:
        db_table = 'results_processingresult' # Tên bảng rõ ràng
        verbose_name = "Kết quả Xử lý"
        verbose_name_plural = "Kết quả Xử lý"
        ordering = ['-received_at', '-detection_timestamp'] # Sắp xếp kết quả mới nhất lên đầu

    def __str__(self):
        if self.source_upload:
            return f"Kết quả cho Upload ID {self.source_upload.id} nhận lúc {self.received_at.strftime('%Y-%m-%d %H:%M')}"
        else:
            return f"Kết quả từ Camera RPi nhận lúc {self.received_at.strftime('%Y-%m-%d %H:%M')}"

    # (Tùy chọn) Phương thức helper để lấy danh sách côn trùng
    # def get_detected_insects_list(self):
    #     try:
    #         # Giả sử detected_insects_json là list các dict
    #         return self.detected_insects_json if isinstance(self.detected_insects_json, list) else []
    #     except:
    #         return []
