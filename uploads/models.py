# uploads/models.py
from django.db import models
from accounts.models import CustomUser # Import model User tùy chỉnh
import uuid
import os

def get_user_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    user_id_str = str(instance.uploaded_by.id) if instance.uploaded_by else 'anonymous'
    filename = f"user_{user_id_str}_{uuid.uuid4()}.{ext}"
    return os.path.join('user_uploads', user_id_str, filename)

class UserUpload(models.Model):
    # ---- THÊM CÁC LỰA CHỌN TRẠNG THÁI ----
    STATUS_PENDING = 'pending'
    STATUS_ASSIGNED = 'assigned_to_rpi' # Hoặc 'processing_by_rpi'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Đang chờ xử lý'),
        (STATUS_ASSIGNED, 'Đã giao cho RPi'),
        (STATUS_COMPLETED, 'Hoàn thành'),
        (STATUS_FAILED, 'Thất bại'),
    ]
    # ------------------------------------

    uploaded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE, 
        related_name='uploads',
        verbose_name="Người tải lên"
    )
    file = models.FileField(upload_to=get_user_upload_path, verbose_name="File gốc")
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời điểm tải lên")
    
    # ---- THÊM TRƯỜNG STATUS VÀO ĐÂY ----
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING, # Trạng thái mặc định khi mới upload
        verbose_name="Trạng thái xử lý"
    )
    # ---------------------------------
    # (Tùy chọn) Thêm trường updated_at nếu bạn muốn theo dõi thời gian cập nhật status
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")


    class Meta:
        db_table = 'uploads_userupload'
        verbose_name = "File Người dùng Tải lên"
        verbose_name_plural = "File Người dùng Tải lên"
        ordering = ['-upload_time']

    def __str__(self):
        email = self.uploaded_by.email if self.uploaded_by else 'N/A'
        ts = self.upload_time.strftime('%Y-%m-%d %H:%M')
        filename = os.path.basename(self.file.name) if self.file else f"Upload {self.id}"
        # Hiển thị cả status trong __str__ để dễ theo dõi trong Admin
        return f"{filename} by {email} at {ts} [{self.get_status_display()}]"