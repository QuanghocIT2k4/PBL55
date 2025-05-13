# accounts/urls.py
from django.urls import path, include # <<< THÊM include
from rest_framework.routers import DefaultRouter # <<< THÊM DefaultRouter
from . import views # Import các view hiện có
from .views import AdminUserViewSet # <<< THÊM import AdminUserViewSet

app_name = 'accounts'

# Tạo router cho AdminUserViewSet
admin_router = DefaultRouter()
# Đăng ký AdminUserViewSet với prefix 'admin/users'
# Router sẽ tạo các URL cho list, create, retrieve, update, partial_update, destroy
admin_router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

urlpatterns = [
    # URLs cho người dùng tự phục vụ
    path('register/', views.RegisterView.as_view(), name='user_register'),
    path('login/', views.CustomLoginView.as_view(), name='user_login'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change_password'),

    # Bao gồm các URLs được tạo tự động bởi admin_router
    # Các URL này sẽ có dạng /admin/users/, /admin/users/{id}/, ...
    path('', include(admin_router.urls)),
]

