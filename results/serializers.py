# results/serializers.py
from rest_framework import serializers
from .models import ProcessingResult, UserUpload # Import cả UserUpload để kiểm tra ID
from uploads.serializers import UserUploadSerializer # Để hiển thị thông tin upload gốc

# Serializer để validate input từ RPi khi gửi kết quả
class RPiResultInputSerializer(serializers.Serializer):
    image_base64 = serializers.CharField(required=True)
    timestamp = serializers.DateTimeField(required=True, input_formats=['iso-8601'])
    # insects là một list các dictionary, JSONField xử lý tốt việc này
    insects = serializers.JSONField(required=True)
    source_upload_id = serializers.IntegerField(required=False, allow_null=True) # Cho phép null hoặc không có

    def validate_source_upload_id(self, value):
        """Kiểm tra xem UserUpload ID có tồn tại không nếu được cung cấp."""
        if value is not None:
            if not UserUpload.objects.filter(pk=value).exists():
                raise serializers.ValidationError(f"Không tìm thấy UserUpload với ID={value}.")
            # (Tùy chọn) Kiểm tra xem upload_id này đã có kết quả chưa nếu dùng OneToOneField
            if ProcessingResult.objects.filter(source_upload_id=value).exists():
                 raise serializers.ValidationError(f"Kết quả cho UserUpload ID={value} đã tồn tại.")
        return value

# Serializer để hiển thị kết quả xử lý đã lưu
class ProcessingResultOutputSerializer(serializers.ModelSerializer):
    # Hiển thị thông tin chi tiết của upload gốc nếu có
    source_upload_details = UserUploadSerializer(source='source_upload', read_only=True)
    # Có thể thêm SerializerMethodField để xử lý URL ảnh nếu cần
    # processed_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProcessingResult
        fields = [
            'id',
            'source_upload', # Trả về ID của upload gốc
            'source_upload_details', # Trả về thông tin chi tiết upload gốc
            'processed_image', # Trả về đường dẫn tương đối
            # 'processed_image_url', # URL tuyệt đối (nếu implement)
            'detection_timestamp',
            'detected_insects_json',
            'received_at',
        ]
        read_only_fields = fields # Thường thì API kết quả chỉ để đọc

    # def get_processed_image_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.processed_image and request:
    #         return request.build_absolute_uri(obj.processed_image.url)
    #     return None