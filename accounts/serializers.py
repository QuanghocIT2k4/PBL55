# accounts/serializers.py
from rest_framework import serializers
from .models import CustomUser
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Khởi tạo PasswordHasher một lần để tái sử dụng
ph = PasswordHasher()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer để hiển thị thông tin người dùng (không hiển thị password hash).
    Thường dùng để trả về thông tin profile hoặc trong danh sách user (cho admin).
    """
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = CustomUser
        # Các trường muốn hiển thị qua API
        fields = ('id', 'email', 'first_name', 'last_name', 'user_type', 'user_type_display', 'is_active', 'created_at', 'updated_at')
        # Các trường chỉ đọc, không cho phép cập nhật trực tiếp qua API profile thông thường
        read_only_fields = ('id', 'email', 'user_type', 'user_type_display', 'created_at', 'updated_at', 'is_active')
        # Lưu ý: Quyền thay đổi is_active hoặc user_type nên được xử lý trong view admin riêng biệt

class RegisterSerializer(serializers.ModelSerializer):
    """Serializer để xử lý việc đăng ký tài khoản mới."""
    password = serializers.CharField(
        write_only=True,    # Chỉ nhận, không trả ra
        required=True,
        min_length=8,       # Nên đặt quy tắc độ dài tối thiểu
        style={'input_type': 'password'},
        label="Mật khẩu"
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label="Xác nhận mật khẩu"
    )
    # Thêm user_type để cho phép tạo Admin từ API (cần bảo vệ API này)
    user_type = serializers.ChoiceField(choices=CustomUser.USER_TYPE_CHOICES, default=CustomUser.USER_TYPE_CHOICES[1][0]) # Mặc định là REGULAR

    class Meta:
        model = CustomUser
        # Các trường cần cung cấp khi đăng ký
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'user_type')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            # Email là bắt buộc (mặc định)
        }

    def validate_email(self, value):
        """Kiểm tra email đã tồn tại chưa."""
        if CustomUser.objects.filter(email__iexact=value).exists(): # Kiểm tra không phân biệt hoa thường
            raise serializers.ValidationError("Địa chỉ email này đã được sử dụng.")
        return value

    def validate(self, attrs):
        """Kiểm tra mật khẩu xác nhận có khớp không."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Mật khẩu xác nhận không khớp."})
        return attrs

    def create(self, validated_data):
        """Tạo người dùng mới và hash mật khẩu bằng Argon2."""
        # Loại bỏ password2 vì không có trong model
        validated_data.pop('password2')
        # Lấy mật khẩu gốc
        raw_password = validated_data.pop('password')
        # Hash mật khẩu
        hashed_password = ph.hash(raw_password)
        # Gán mật khẩu đã hash vào data
        validated_data['password_hash'] = hashed_password

        # Tạo user
        # validated_data bây giờ chứa: email, password_hash, first_name, last_name, user_type
        user = CustomUser.objects.create(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    """Serializer để nhận và validate dữ liệu đăng nhập."""
    email = serializers.EmailField(required=True, label="Email")
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label="Mật khẩu"
    )
    # Không cần validate gì thêm ở đây, logic kiểm tra mật khẩu sẽ ở trong View
    
class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer để xử lý việc đổi mật khẩu cho người dùng đang đăng nhập.
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        label="Mật khẩu cũ"
    )
    new_password1 = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8, # Áp dụng lại quy tắc độ dài
        style={'input_type': 'password'},
        label="Mật khẩu mới"
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        label="Xác nhận mật khẩu mới"
    )

    def validate_old_password(self, value):
        """
        Kiểm tra mật khẩu cũ có đúng không.
        Cần truyền 'request' vào context của serializer từ View.
        """
        user = self.context['request'].user # Lấy user từ context (do simplejwt gắn vào)
        # Lấy đối tượng CustomUser thật từ DB dựa trên ID trong token
        try:
            current_user = CustomUser.objects.get(pk=user.id)
        except CustomUser.DoesNotExist:
             # Lỗi này không nên xảy ra nếu token hợp lệ
            raise serializers.ValidationError("Người dùng không tồn tại.")

        # Xác thực mật khẩu cũ bằng Argon2
        try:
            if not ph.verify(current_user.password_hash, value):
                 raise serializers.ValidationError("Mật khẩu cũ không chính xác.")
        except VerifyMismatchError:
             raise serializers.ValidationError("Mật khẩu cũ không chính xác.")
        except Exception as e:
             # Log lỗi nếu cần
             print(f"Error verifying old password: {e}")
             raise serializers.ValidationError("Lỗi khi kiểm tra mật khẩu cũ.")
        return value

    def validate(self, attrs):
        """Kiểm tra mật khẩu mới và xác nhận có khớp không."""
        if attrs['new_password1'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password1": "Mật khẩu mới và xác nhận không khớp."})

        # (Tùy chọn) Kiểm tra mật khẩu mới có trùng mật khẩu cũ không
        if attrs['new_password1'] == attrs['old_password']:
             raise serializers.ValidationError({"new_password1": "Mật khẩu mới không được trùng với mật khẩu cũ."})

        # (Tùy chọn) Có thể thêm các quy tắc phức tạp khác cho mật khẩu mới ở đây
        # ví dụ: validate_password từ django.contrib.auth.password_validation (nhưng bạn muốn tránh?)

        return attrs

    def save(self, **kwargs):
        """Hash và lưu mật khẩu mới."""
        password = self.validated_data['new_password1']
        user = self.context['request'].user
        # Lấy đối tượng CustomUser thật
        try:
            current_user = CustomUser.objects.get(pk=user.id)
        except CustomUser.DoesNotExist:
            # Như trên, không nên xảy ra
            raise serializers.ValidationError("Người dùng không tồn tại.")

        # Hash mật khẩu mới
        current_user.password_hash = ph.hash(password)
        current_user.save()
        return current_user
    
    # --- CHỈ GIỮ LẠI CLASS NÀY ĐỂ TEST ---
class AdminUserManagementSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False, # Sẽ validate trong create
        min_length=8,
        style={'input_type': 'password'},
        label="Mật khẩu"
    )
    # Tạm thời bỏ user_type_display để giảm phụ thuộc
    # user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = CustomUser
        # Chỉ lấy các trường thật sự cần cho test này
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'user_type', 'is_active',
            'password', # Trường password để tạo mới
            # 'created_at', 'updated_at' # Tạm bỏ qua
        )
        read_only_fields = ('id', 'email') # Email không cho sửa

    def create(self, validated_data):
        print("DEBUG: AdminUserManagementSerializer - Bắt đầu create")
        if 'password' not in validated_data:
            raise serializers.ValidationError({'password': 'Mật khẩu là bắt buộc khi tạo người dùng mới.'})
        
        raw_password = validated_data.pop('password')
        
        # Kiểm tra email trùng lặp cơ bản
        email = validated_data.get('email')
        if email and CustomUser.objects.filter(email__iexact=email).exists():
             raise serializers.ValidationError({"email": f"Địa chỉ email '{email}' đã được sử dụng."})

        # Hash mật khẩu - Đảm bảo 'ph' đã được khởi tạo thành công
        try:
             validated_data['password_hash'] = ph.hash(raw_password)
        except Exception as hash_error:
             print(f"ERROR: Không thể hash mật khẩu: {hash_error}")
             raise serializers.ValidationError("Lỗi hệ thống khi xử lý mật khẩu.")

        print(f"DEBUG: AdminUserManagementSerializer - Dữ liệu tạo user (trước create): {validated_data}")
        user = CustomUser.objects.create(**validated_data)
        print(f"DEBUG: AdminUserManagementSerializer - User đã tạo: {user.id}")
        return user

    def update(self, instance, validated_data):
        print(f"DEBUG: AdminUserManagementSerializer - Bắt đầu update user {instance.id}")
        validated_data.pop('password', None) # Không cho update password

        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.user_type = validated_data.get('user_type', instance.user_type)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save(update_fields=['first_name', 'last_name', 'user_type', 'is_active', 'updated_at'])
        print(f"DEBUG: AdminUserManagementSerializer - User đã update: {instance.id}")
        return instance

    print("DEBUG: accounts/serializers.py - Đã định nghĩa xong AdminUserManagementSerializer")
