# accounts/models.py
from django.db import models

class CustomUser(models.Model):
    USER_TYPE_CHOICES = [
        ('ADMIN', 'Quản trị viên'),
        ('REGULAR', 'Người dùng thường'),
    ]
    email = models.EmailField(max_length=255, unique=True, db_index=True, verbose_name="Email Đăng Nhập")
    password_hash = models.CharField(max_length=255, verbose_name="Mật khẩu (Hashed)") # Sẽ hash bằng thư viện ngoài
    first_name = models.CharField(max_length=150, blank=True, verbose_name="Tên")
    last_name = models.CharField(max_length=150, blank=True, verbose_name="Họ")
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='REGULAR', verbose_name="Loại tài khoản")
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'accounts_customuser'
        verbose_name = "Tài khoản Người dùng"
        verbose_name_plural = "Tài khoản Người dùng"
        ordering = ['email']

    def __str__(self):
        return f"{self.email} ({self.get_user_type_display()})"
    
    # ----- THÊM CÁC THUỘC TÍNH PROPERTY VÀO ĐÂY -----
    @property
    def is_admin(self):
        """Kiểm tra xem user có phải là Admin không."""
        return self.user_type == 'ADMIN'

    @property
    def is_regular_user(self):
        """Kiểm tra xem user có phải là User thường không."""
        return self.user_type == 'REGULAR'
    # -----------------------------------------------