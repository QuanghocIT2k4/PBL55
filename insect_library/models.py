# insect_library/models.py
from django.db import models

class InsectReference(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="Tên Định Danh (VD: muoi_vang)")
    scientific_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Tên Khoa Học")
    description = models.TextField(blank=True, null=True, verbose_name="Mô Tả Đặc Điểm")
    habitat = models.TextField(blank=True, null=True, verbose_name="Khu Vực Sinh Sống")
    host_plants = models.TextField(blank=True, null=True, verbose_name="Loài Cây Bị Gây Hại")
    treatment = models.TextField(blank=True, null=True, verbose_name="Cách Xử Lý/Phòng Trừ")
    active_season = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mùa Hoạt Động")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        db_table = 'insect_library_insectreference'
        verbose_name = "Thông tin Côn trùng Tham khảo"
        verbose_name_plural = "Thông tin Côn trùng Tham khảo"
        ordering = ['name']

    def __str__(self):
        return self.name