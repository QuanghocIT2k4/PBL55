# insect_library/views.py
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework import filters # Import SearchFilter, OrderingFilter

# Import Model và Serializer từ app hiện tại
from .models import InsectReference
from .serializers import InsectReferenceSerializer
# Import custom permissions từ app accounts
from accounts.permissions import IsAuthenticatedCustom, IsAdminUserType

class InsectReferenceViewSet(viewsets.ModelViewSet):
    """
    API endpoint cho phép xem (User/Admin) và quản lý (Admin)
    thông tin côn trùng tham khảo.
    Hỗ trợ tìm kiếm và sắp xếp.

    Ví dụ:
    - GET /api/library/insects/?search=vang
    - GET /api/library/insects/?ordering=scientific_name
    """
    queryset = InsectReference.objects.all().order_by('name')
    serializer_class = InsectReferenceSerializer

    # Kích hoạt Tìm kiếm và Sắp xếp
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    
    # Các trường để tìm kiếm (search)
    search_fields = [
        'name',
        'scientific_name',
        'description',
        'habitat',
        'host_plants',
        'treatment',
        'active_season',
    ]
    
    # Các trường cho phép sắp xếp (ordering)
    ordering_fields = ['name', 'scientific_name', 'created_at', 'updated_at'] 
    
    # Sắp xếp mặc định
    ordering = ['name'] 

    def get_permissions(self):
        """
        Gán quyền truy cập động dựa trên hành động (action).
        """
        if self.action in ['list', 'retrieve']:
            # Yêu cầu đăng nhập để xem danh sách và chi tiết
            permission_classes = [IsAuthenticatedCustom]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Chỉ Admin được tạo, sửa, xóa
            permission_classes = [IsAdminUserType]
        else:
            # Các action khác (nếu có) mặc định yêu cầu đăng nhập
            permission_classes = [IsAuthenticatedCustom]
        return [permission() for permission in permission_classes]