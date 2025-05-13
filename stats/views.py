# stats/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from datetime import date, timedelta, datetime # Import datetime đầy đủ
from collections import defaultdict
import json # Để parse JSON an toàn hơn

# Import models và permissions
from results.models import ProcessingResult # <<< QUAN TRỌNG: Import từ results
from accounts.permissions import IsAuthenticatedCustom # <<< Import permission

class FrequencyStatsView(APIView):
    """
    API endpoint để lấy dữ liệu tần suất xuất hiện côn trùng.
    Mỗi loại côn trùng chỉ được tính tối đa 1 lần cho mỗi ngày nó xuất hiện.
    GET: /api/stats/frequency/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """
    permission_classes = [IsAuthenticatedCustom] # Yêu cầu đăng nhập để xem thống kê

    def get(self, request, *args, **kwargs):
        # 1. Lấy và Validate Ngày Tháng từ Query Params
        try:
            today = date.today()
            end_date_str = request.query_params.get('end_date', today.isoformat())
            default_start_date = today - timedelta(days=6)
            start_date_str = request.query_params.get('start_date', default_start_date.isoformat())
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
            if start_date > end_date:
                raise ValueError("Ngày bắt đầu không thể sau ngày kết thúc.")
        except ValueError as e:
            return Response({'error': f'Ngày không hợp lệ: {e}. Dùng định dạng YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Truy vấn dữ liệu thô từ DB trong khoảng thời gian
        results_queryset = ProcessingResult.objects.filter(
            detection_timestamp__date__range=[start_date, end_date]
        ).values_list('detection_timestamp__date', 'detected_insects_json')

        # 3. Xử lý trong Python để lấy các cặp (Ngày, Tên côn trùng) duy nhất
        daily_presence = set()
        all_insect_names = set()

        for detection_date, insects_json_str in results_queryset:
            insects = []
            try:
                if isinstance(insects_json_str, str):
                    insects = json.loads(insects_json_str)
                elif isinstance(insects_json_str, list):
                    insects = insects_json_str
                if not isinstance(insects, list): continue

                for insect_data in insects:
                    if isinstance(insect_data, dict) and 'name' in insect_data:
                        insect_name = insect_data['name']
                        if insect_name:
                            presence_entry = (detection_date, insect_name)
                            daily_presence.add(presence_entry)
                            all_insect_names.add(insect_name)
            except json.JSONDecodeError: continue
            except Exception as e:
                print(f"Error processing record for {detection_date}: {e}")
                continue

        # 4. Chuẩn bị dữ liệu cho Chart.js
        date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        labels = [d.strftime('%Y-%m-%d') for d in date_list]
        date_index_map = {d: i for i, d in enumerate(date_list)}
        sorted_insect_names = sorted(list(all_insect_names))
        datasets = []
        for name in sorted_insect_names:
            data_points = [0] * len(labels)
            for day, insect_name_found in daily_presence:
                if insect_name_found == name and day in date_index_map:
                    index = date_index_map[day]
                    data_points[index] = 1
            datasets.append({'label': name, 'data': data_points})

        # 5. Trả về Response JSON
        chart_data = {
            'labels': labels,
            'datasets': datasets,
        }
        return Response(chart_data, status=status.HTTP_200_OK)