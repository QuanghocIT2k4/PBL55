# uploads/serializers.py
from rest_framework import serializers
from .models import UserUpload
# Import serializer user nếu cần hiển thị thông tin người upload chi tiết
# Giả sử bạn đã tạo UserSerializer trong accounts/serializers.py
try:
    from accounts.serializers import UserSerializer
except ImportError:
    # Dự phòng nếu UserSerializer không tồn tại hoặc có lỗi import vòng tròn
    class UserSerializer(serializers.Serializer):
        id = serializers.IntegerField(read_only=True)
        email = serializers.EmailField(read_only=True)
        # Thêm các trường khác nếu cần

class UserUploadSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị thông tin file người dùng đã tải lên.
    Cũng được dùng bởi CreateAPIView để trả về response sau khi tạo.
    """
    # Hiển thị thông tin cơ bản của người upload (chỉ đọc)
    # `source='uploaded_by'` nghĩa là lấy dữ liệu từ trường 'uploaded_by' của model UserUpload
    uploaded_by_info = UserSerializer(source='uploaded_by', read_only=True)

    class Meta:
        model = UserUpload
        # Các trường sẽ được bao gồm trong JSON response
        fields = (
            'id',
            'uploaded_by', # Vẫn hiển thị ID của người upload
            'uploaded_by_info', # Hiển thị thông tin chi tiết hơn (từ UserSerializer)
            'file', # Hiển thị đường dẫn tương đối của file
            'upload_time'
        )
        # Các trường chỉ được đọc, không nhận giá trị từ input khi tạo/cập nhật
        # QUAN TRỌNG: Thêm 'uploaded_by' vào đây để DRF không yêu cầu nó trong input body
        read_only_fields = (
            'id',
            'upload_time',
            'uploaded_by_info',
            'uploaded_by' # <<< THÊM VÀO ĐÂY
        )
        # Không cần extra_kwargs cho 'file' ở đây vì nó được xử lý trong perform_create