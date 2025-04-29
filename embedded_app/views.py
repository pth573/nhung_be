from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import db
from .models import Route, Alert, SensorData
from .serializers import SensorDataSerializer, RouteSerializer, AlertSerializer
import threading
from ai_module.motion_predictor import MotionPredictor
import json
import time

# Khởi tạo MotionPredictor từ ai_module
motion_predictor = MotionPredictor()

# Biến toàn cục
latest_data = None
active_alert = None
data_lock = threading.Lock()
last_processed_timestamp = 0
previous_data = None  # Lưu dữ liệu trước đó để so sánh sự thay đổi

def firebase_listener():
    ref = db.reference('ESP32')

    def callback(event):
        global latest_data, active_alert, last_processed_timestamp, previous_data

        data = event.data

        # Kiểm tra dữ liệu có tồn tại và hợp lệ
        if data is None:
            print("Nhận dữ liệu rỗng, có thể do node bị xóa")
            return

        # Kiểm tra nếu dữ liệu là dictionary
        if not isinstance(data, dict):
            print(f"Định dạng dữ liệu không hợp lệ, cần kiểu dictionary: {data}")
            return

        # Tạo timestamp thủ công để kiểm tra dữ liệu mới
        current_timestamp = int(time.time() * 1000)  # Timestamp dạng millisecond

        # Chuẩn bị dữ liệu mới
        new_data = {
            'latitude': data.get('Latitude', 0),
            'longitude': data.get('Longitude', 0),
            'AccX': data.get('AccX', 0),
            'AccY': data.get('AccY', 0),
            'AccZ': data.get('AccZ', 0),
            'GyroX': data.get('GyroX', 0),
            'GyroY': data.get('GyroY', 0),
            'GyroZ': data.get('GyroZ', 0),
            'Temperature': data.get('Temperature', 0),
            'vibration_detected': False,
            'timestamp': str(current_timestamp)
        }

        # Kiểm tra sự thay đổi nếu có dữ liệu trước đó
        if previous_data:
            # Xác định các trường đã thay đổi
            changed_fields = {}
            for key in new_data:
                if key in previous_data and new_data[key] != previous_data[key]:
                    changed_fields[key] = {
                        'old': previous_data[key],
                        'new': new_data[key]
                    }
            
            # if changed_fields:
            #     print("\n=== Phát hiện thay đổi trong dữ liệu ===")
            #     for field, values in changed_fields.items():
            #         print(f"{field}: {values['old']} -> {values['new']}")
            
            # Nếu chỉ có timestamp thay đổi, bỏ qua
            if len(changed_fields) == 1 and 'timestamp' in changed_fields:
                # print("Chỉ có timestamp thay đổi, bỏ qua")
                return
            
            # Nếu không có thay đổi, bỏ qua xử lý
            if not changed_fields:
                # print("Không có thay đổi trong dữ liệu, bỏ qua")
                return
        
        # Lưu dữ liệu hiện tại để so sánh trong lần tiếp theo
        previous_data = new_data.copy()
        
        # Chuẩn bị dữ liệu cho dự đoán AI
        features = [
            new_data['AccX'], new_data['AccY'], new_data['AccZ'],
            new_data['GyroX'], new_data['GyroY'], new_data['GyroZ']
        ]
        
        # Sử dụng MotionPredictor để dự đoán rung lắc
        prediction = motion_predictor.predict(features)
        new_data['vibration_detected'] = bool(prediction)

        # In dữ liệu cảm biến và dự đoán
        print(f"\n=== Nhận dữ liệu mới ===")
        print(f"Dữ liệu cảm biến: {json.dumps(new_data, indent=2, ensure_ascii=False)}")
        print(f"Dự đoán rung lắc: {'Có rung' if prediction == 1 else 'Không rung'}")

        # Lưu dữ liệu cảm biến vào SQLite
        SensorData.objects.create(
            latitude=new_data['latitude'],
            longitude=new_data['longitude'],
            AccX=new_data['AccX'],
            AccY=new_data['AccY'],
            AccZ=new_data['AccZ'],
            GyroX=new_data['GyroX'],
            GyroY=new_data['GyroY'],
            GyroZ=new_data['GyroZ'],
            temperature=new_data['Temperature'],
            vibration_detected=new_data['vibration_detected'],
            timestamp=str(current_timestamp)
        )

        # Xử lý cảnh báo rung lắc
        handle_vibration_alert(str(current_timestamp), new_data, prediction)

        # Lưu lộ trình vào SQLite nếu có tọa độ hợp lệ
        if new_data['latitude'] != 0 and new_data['longitude'] != 0:
            Route.objects.create(
                latitude=new_data['latitude'],
                longitude=new_data['longitude'],
                time=str(current_timestamp)  
            )

        # Cập nhật dữ liệu mới nhất và timestamp đã xử lý
        with data_lock:
            global latest_data
            latest_data = new_data
            last_processed_timestamp = current_timestamp

    try:
        ref.listen(callback)
    except Exception as e:
        print(f"Lỗi trong Firebase listener: {e}")

def handle_vibration_alert(timestamp, data, prediction):
    global active_alert

    if prediction == 1:
        if active_alert is None:
            active_alert = Alert.objects.create(
                start_time=timestamp,
                end_time=None,
                latitude=data['latitude'],
                longitude=data['longitude'],
                is_active=True
            )
    elif prediction == 0 and active_alert is not None:
        active_alert.end_time = timestamp
        active_alert.is_active = False
        active_alert.save()
        active_alert = None

# Khởi động worker lắng nghe Firebase
listener_thread = threading.Thread(target=firebase_listener, daemon=True)
listener_thread.start()

class CurrentSensorDataView(APIView):
    def get(self, request):
        with data_lock:
            if latest_data is None:
                return Response({"error": "Chưa có dữ liệu nào"}, status=status.HTTP_404_NOT_FOUND)
            
            # Trả về dữ liệu mới nhất
            return Response(SensorDataSerializer({
                'timestamp': latest_data['timestamp'],
                'latitude': latest_data['latitude'],
                'longitude': latest_data['longitude'],
                'AccX': latest_data['AccX'],
                'AccY': latest_data['AccY'],
                'AccZ': latest_data['AccZ'],
                'GyroX': latest_data['GyroX'],
                'GyroY': latest_data['GyroY'],
                'GyroZ': latest_data['GyroZ'],
                'temperature': latest_data['Temperature'],
                'vibration_detected': latest_data['vibration_detected']
            }).data)

class SensorDataHistoryView(APIView):
    def get(self, request):
        # Lấy tham số limit và time_range từ query
        limit = int(request.query_params.get('limit', 50))
        time_range = request.query_params.get('time_range', None)  # time_range dạng millisecond

        # Lấy timestamp hiện tại
        current_timestamp = int(time.time() * 1000)

        # Lọc dữ liệu
        if time_range:
            threshold_timestamp = str(current_timestamp - int(time_range))
            sensor_data = SensorData.objects.filter(timestamp__gte=threshold_timestamp).order_by('-timestamp')
        else:
            sensor_data = SensorData.objects.all().order_by('-timestamp')

        # Giới hạn số lượng bản ghi
        sensor_data = sensor_data[:limit]
        
        if not sensor_data:
            return Response({"error": "Không tìm thấy dữ liệu cảm biến"}, status=status.HTTP_404_NOT_FOUND)

        # Trả về dữ liệu đã được serialize
        serializer = SensorDataSerializer(sensor_data, many=True)
        return Response({'sensor_data': serializer.data})

class RouteView(APIView):
    def get(self, request):
        routes = Route.objects.all()
        serializer = RouteSerializer(routes, many=True)
        return Response({'route': serializer.data})

class RecentRouteView(APIView):
    def get(self, request):
        # Lấy tham số limit từ query (mặc định là 10)
        limit = int(request.query_params.get('limit', 10))
        
        # Lấy các điểm lộ trình mới nhất, sắp xếp theo time giảm dần
        routes = Route.objects.all().order_by('-time')[:limit]
        
        if not routes:
            return Response({"error": "Không tìm thấy dữ liệu lộ trình"}, status=status.HTTP_404_NOT_FOUND)

        serializer = RouteSerializer(routes, many=True)
        return Response({'route': serializer.data})

class AlertView(APIView):
    def get(self, request):
        alerts = Alert.objects.all()
        serializer = AlertSerializer(alerts, many=True)
        return Response(serializer.data)

class AlertDetailView(APIView):
    def get(self, request, start_time):
        try:
            alert = Alert.objects.get(start_time=start_time)
            serializer = AlertSerializer(alert)
            return Response(serializer.data)
        except Alert.DoesNotExist:
            return Response({"error": "Không tìm thấy cảnh báo"}, status=status.HTTP_404_NOT_FOUND)

class DeleteSensorDataView(APIView):
    def delete(self, request):
        try:
            count = SensorData.objects.count()
            SensorData.objects.all().delete()
            return Response({"message": f"Đã xóa thành công {count} bản ghi dữ liệu cảm biến."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteRouteDataView(APIView):
    def delete(self, request):
        try:
            count = Route.objects.count()
            Route.objects.all().delete()
            return Response({"message": f"Đã xóa thành công {count} bản ghi lộ trình."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteAlertDataView(APIView):
    def delete(self, request):
        try:
            count = Alert.objects.count()
            Alert.objects.all().delete()
            # Đặt lại active_alert về None nếu đang có cảnh báo active
            global active_alert
            active_alert = None
            return Response({"message": f"Đã xóa thành công {count} bản ghi cảnh báo."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)