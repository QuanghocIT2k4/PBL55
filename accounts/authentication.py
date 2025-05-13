# accounts/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.utils.translation import gettext_lazy as _
# Import model CustomUser của bạn
from .models import CustomUser
# Import TokenUser (có thể không cần nữa nếu get_user trả về CustomUser)
# from rest_framework_simplejwt.models import TokenUser

# --- THÊM IMPORT NÀY ---
from rest_framework_simplejwt.settings import api_settings as simplejwt_settings

class CustomJWTAuthentication(JWTAuthentication):
    """
    Lớp xác thực JWT tùy chỉnh để tìm kiếm trong model CustomUser.
    """

    def get_user(self, validated_token):
        """
        Ghi đè phương thức này để tìm kiếm trong bảng CustomUser.
        """
        try:
            # --- Lấy tên claim và field từ settings ---
            user_id_claim = simplejwt_settings.USER_ID_CLAIM
            user_id_field = simplejwt_settings.USER_ID_FIELD
            # ----------------------------------------

            # Lấy user ID từ payload của token đã được validate
            user_id = validated_token[user_id_claim] # Sử dụng biến vừa lấy

        except KeyError:
            raise InvalidToken(_("Token không chứa định danh người dùng hợp lệ"))

        # Tìm kiếm trực tiếp trong model CustomUser của bạn bằng ID lấy được
        try:
            user = CustomUser.objects.get(**{user_id_field: user_id}) # Sử dụng biến vừa lấy
        except CustomUser.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")
        except Exception as e:
            print(f"CustomJWTAuthentication: Error fetching CustomUser with id {user_id}: {e}")
            raise AuthenticationFailed(_("Lỗi khi truy vấn người dùng."), code="user_query_error")

        # Kiểm tra user có active không
        if not user.is_active:
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        # Trả về đối tượng CustomUser đã tìm thấy
        return user