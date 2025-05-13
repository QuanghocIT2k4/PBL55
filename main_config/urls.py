# main_config/urls.py

from django.urls import path, include
from django.conf import settings      # Thêm nếu cần cấu hình media/static
from django.conf.urls.static import static # Thêm nếu cần cấu hình media/static

urlpatterns = [
    # DÒNG QUAN TRỌNG CẦN THÊM/SỬA:
    path('api/accounts/', include('accounts.urls')),

    # Thêm các include cho các app khác ở đây nếu có
    path('api/library/', include('insect_library.urls')),

    path('api/uploads/', include('uploads.urls')),
    path('api/results/', include('results.urls')),
    path('api/stats/', include('stats.urls')), 
    path('api/livefeed/', include('livefeed.urls')),
]

# (Tùy chọn) Thêm phần này nếu bạn muốn serve file media khi DEBUG=True
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Dòng này rất quan trọng cho việc xem ảnh khi dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)