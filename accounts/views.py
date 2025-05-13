# accounts/views.py
from django.http import Http404
from rest_framework import generics, permissions, status, viewsets # <<< THÊM viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
# Import token của SimpleJWT để tạo thủ công
from rest_framework_simplejwt.tokens import AccessToken
# Import Permission AllowAny và Custom Permission mới
from rest_framework.permissions import AllowAny
from .permissions import IsAuthenticatedCustom, IsAdminUserType # <<< Giữ nguyên

# Import từ app accounts
from .models import CustomUser
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    AdminUserManagementSerializer
)

# Import Argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Khởi tạo PasswordHasher
ph = PasswordHasher()

# --- View Đăng Ký ---
class RegisterView(generics.CreateAPIView):
    """
    API endpoint để đăng ký người dùng mới (mặc định là REGULAR).
    POST: /api/accounts/register/
    Không yêu cầu xác thực.
    """
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    # Logic tạo user và hash password nằm trong RegisterSerializer.create

# --- View Đăng Nhập Tùy Chỉnh ---
class CustomLoginView(APIView):
    """
    API endpoint để đăng nhập bằng email và password tùy chỉnh.
    Trả về access token nếu thành công.
    POST: /api/accounts/login/
    Không yêu cầu xác thực.
    """
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        password = serializer.validated_data.get('password')

        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Email hoặc mật khẩu không đúng."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "Tài khoản này đã bị vô hiệu hóa."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            ph.verify(user.password_hash, password)
            if ph.check_needs_rehash(user.password_hash):
                user.password_hash = ph.hash(password)
                user.save(update_fields=['password_hash', 'updated_at'])
        except VerifyMismatchError:
            return Response({"detail": "Email hoặc mật khẩu không đúng."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"Password verification error for {email}: {e}")
            return Response({"detail": "Lỗi trong quá trình xác thực."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        access_token = AccessToken.for_user(user)
        # Thêm các claim tùy chỉnh vào token payload
        access_token['user_type'] = user.user_type
        access_token['email'] = user.email

        data = {
            'access': str(access_token),
            # Có thể trả về thêm thông tin user nếu muốn
            # 'user': UserSerializer(user).data 
        }
        return Response(data, status=status.HTTP_200_OK)


# --- View Xem và Cập nhật Profile ---
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint để xem (GET) và cập nhật (PUT/PATCH)
    thông tin profile của người dùng đang đăng nhập (chỉ first_name, last_name).
    Sử dụng CustomJWTAuthentication và IsAuthenticatedCustom.
    GET, PUT, PATCH: /api/accounts/profile/
    Yêu cầu xác thực bằng JWT hợp lệ.
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer # UserSerializer chỉ cho sửa first_name, last_name
    permission_classes = (IsAuthenticatedCustom,) 

    def get_object(self):
        if not (hasattr(self.request, 'user') and isinstance(self.request.user, CustomUser)):
             # Trường hợp này không nên xảy ra nếu IsAuthenticatedCustom hoạt động đúng
             # và CustomJWTAuthentication trả về CustomUser
            user_from_token = getattr(self.request, 'user', None)
            print(f"WARNING in UserProfileView: request.user is not a valid CustomUser. Type: {type(user_from_token)}")
            # Cố gắng lấy lại user từ DB nếu chỉ có ID
            if user_from_token and hasattr(user_from_token, 'id'):
                 try:
                     return CustomUser.objects.get(pk=user_from_token.id)
                 except CustomUser.DoesNotExist:
                     raise Http404("Không tìm thấy người dùng hợp lệ trong DB.")
            raise Http404("Không tìm thấy thông tin người dùng hợp lệ.")
        # Trả về user đã được xác thực và là instance của CustomUser
        return self.request.user

# --- View Đổi Mật khẩu ---
class ChangePasswordView(generics.UpdateAPIView):
    """
    API endpoint để người dùng đang đăng nhập đổi mật khẩu.
    Sử dụng CustomJWTAuthentication và IsAuthenticatedCustom.
    PUT: /api/accounts/password/change/
    Yêu cầu xác thực bằng JWT hợp lệ.
    """
    serializer_class = ChangePasswordSerializer
    model = CustomUser
    permission_classes = (IsAuthenticatedCustom,) 

    def get_object(self, queryset=None):
        # Tương tự UserProfileView, đảm bảo trả về CustomUser
        if not (hasattr(self.request, 'user') and isinstance(self.request.user, CustomUser)):
            user_from_token = getattr(self.request, 'user', None)
            print(f"WARNING in ChangePasswordView: request.user is not a valid CustomUser. Type: {type(user_from_token)}")
            if user_from_token and hasattr(user_from_token, 'id'):
                 try:
                     return CustomUser.objects.get(pk=user_from_token.id)
                 except CustomUser.DoesNotExist:
                     raise Http404("Không tìm thấy người dùng hợp lệ trong DB.")
            raise Http404("Không tìm thấy thông tin người dùng hợp lệ.")
        return self.request.user

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data) 

        if serializer.is_valid(raise_exception=True):
            serializer.save() # Logic lưu và hash mật khẩu mới nằm trong serializer
            return Response({"detail": "Đổi mật khẩu thành công."}, status=status.HTTP_200_OK)
        # Không cần trả về lỗi 400 ở đây nếu raise_exception=True

# ---- THÊM VIEWSET MỚI CHO ADMIN QUẢN LÝ USER ----
class AdminUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint cho phép Admin quản lý người dùng.
    - GET /api/accounts/admin/users/: Lấy danh sách tất cả user.
    - POST /api/accounts/admin/users/: Tạo user mới.
    - GET /api/accounts/admin/users/{id}/: Lấy chi tiết user cụ thể.
    - PUT /api/accounts/admin/users/{id}/: Cập nhật toàn bộ user (trừ password, email).
    - PATCH /api/accounts/admin/users/{id}/: Cập nhật một phần user (trừ password, email).
    - DELETE /api/accounts/admin/users/{id}/: Xóa user.
    """
    queryset = CustomUser.objects.all().order_by('id')
    serializer_class = AdminUserManagementSerializer
    permission_classes = [IsAdminUserType] # Chỉ Admin mới có quyền truy cập ViewSet này

    # Có thể thêm phân trang
    # from rest_framework.pagination import PageNumberPagination
    # pagination_class = PageNumberPagination
    # pagination_class.page_size = 10

    # perform_create và perform_update không cần ghi đè ở đây
    # vì logic đã được xử lý trong AdminUserManagementSerializer.
# --------------------------------------------------