# accounts/permissions.py
from rest_framework import permissions
from .models import CustomUser 

class IsAuthenticatedCustom(permissions.BasePermission):
    message = "Yêu cầu xác thực."
    def has_permission(self, request, view):
        # --- SỬA LẠI CÁCH KIỂM TRA ---
        # Không dùng request.user.is_authenticated
        # Kiểm tra xem request.user có tồn tại và có ID không
        user = getattr(request, 'user', None) 
        return bool(user and getattr(user, 'id', None) is not None)
        # ---------------------------

class IsAdminUserType(permissions.BasePermission):
    message = "Yêu cầu quyền quản trị viên."
    def has_permission(self, request, view):
        # Dùng lại logic kiểm tra xác thực đã sửa
        is_authenticated = bool(request.user and getattr(request.user, 'id', None) is not None) 
        if not is_authenticated:
            return False
        # Kiểm tra is_admin property (giả định CustomJWTAuthentication trả về CustomUser)
        return hasattr(request.user, 'is_admin') and request.user.is_admin

class IsRegularUserType(permissions.BasePermission):
    message = "Chỉ người dùng thường mới được thực hiện hành động này."
    def has_permission(self, request, view):
        is_authenticated = bool(request.user and getattr(request.user, 'id', None) is not None)
        if not is_authenticated:
            return False
        # Kiểm tra is_regular_user property
        return hasattr(request.user, 'is_regular_user') and request.user.is_regular_user

# --- (Tùy chọn) Tạo permission HasRPiAPIKey nếu bạn làm bảo mật RPi ---
# class HasRPiAPIKey(permissions.BasePermission): ...