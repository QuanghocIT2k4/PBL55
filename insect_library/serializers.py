# insect_library/serializers.py
from rest_framework import serializers
from .models import InsectReference

class InsectReferenceSerializer(serializers.ModelSerializer):
    """
    Serializer cho Model InsectReference.
    Dùng cho việc hiển thị danh sách, chi tiết và CRUD (trong API Admin tùy chỉnh).
    """
    class Meta:
        model = InsectReference
        fields = '__all__' # Lấy tất cả các trường trong model
        read_only_fields = ('created_at', 'updated_at') # Không cho phép sửa trực tiếp qua API