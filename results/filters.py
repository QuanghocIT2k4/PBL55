# results/filters.py
import django_filters
from .models import ProcessingResult
import json # Import json

class ProcessingResultFilter(django_filters.FilterSet):
    # Lọc theo khoảng ngày phát hiện (detection_timestamp)
    start_date = django_filters.DateFilter(field_name='detection_timestamp__date', lookup_expr='gte', label='Từ ngày (YYYY-MM-DD)')
    end_date = django_filters.DateFilter(field_name='detection_timestamp__date', lookup_expr='lte', label='Đến ngày (YYYY-MM-DD)')

    # Lọc theo tên côn trùng chứa trong JSONField
    # Sử dụng CharFilter và một phương thức lọc tùy chỉnh
    insect_name = django_filters.CharFilter(method='filter_by_insect_name', label='Tên côn trùng (tìm trong JSON)')

    class Meta:
        model = ProcessingResult
        # Chỉ định các trường khác có thể lọc trực tiếp nếu muốn (ví dụ)
        # fields = ['source_upload__uploaded_by__email'] # Lọc theo email người upload (cho Admin)
        fields = ['start_date', 'end_date', 'insect_name'] # Các filter đã định nghĩa

    def filter_by_insect_name(self, queryset, name, value):
        """
        Lọc các ProcessingResult mà trường detected_insects_json (là một list các dict)
        có chứa ít nhất một dictionary với key 'name' bằng với `value` được cung cấp.

        Lưu ý: Hiệu năng của cách lọc JSON này phụ thuộc vào CSDL backend.
        Cách dùng `__contains` hoạt động tốt trên PostgreSQL, MySQL >= 5.7.8, SQLite >= 3.9.0.
        """
        if not value: # Bỏ qua nếu không có giá trị filter
            return queryset
        
        # Tạo query kiểm tra xem JSON array có chứa object với 'name' khớp không
        # Ví dụ: Tìm các bản ghi mà detected_insects_json chứa {"name": "muoi_vang", ...}
        # hoặc chỉ đơn giản là {"name": "muoi_vang"} nếu bạn chỉ lưu tên.
        # Giả sử cấu trúc là list của các dict có key 'name'.
        return queryset.filter(detected_insects_json__contains=[{'name': value}])

        # Cách khác (kém chính xác hơn, tìm kiếm text đơn giản):
        # return queryset.filter(detected_insects_json__icontains=f'"name": "{value}"')