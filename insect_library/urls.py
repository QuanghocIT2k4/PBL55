# insect_library/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views # Import views từ app này

# Tạo router
router = DefaultRouter()

# Đăng ký InsectReferenceViewSet với router
# Tiền tố URL sẽ là 'insects'
router.register(r'insects', views.InsectReferenceViewSet, basename='insect-reference')

# urlpatterns của app này sẽ bao gồm các URL do router tự động tạo ra
urlpatterns = [
    path('', include(router.urls)),
]

# Router sẽ tự tạo các URL như:
# - insects/ (GET, POST)
# - insects/{pk}/ (GET, PUT, PATCH, DELETE)