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

def firebase_listener():
    ref = db.reference('ESP32')

    def callback(event):
        global latest_data, active_alert, last_processed_timestamp

        data = event.data

        # Kiểm tra dữ liệu có tồn tại và hợp lệ
        if data is None:
            print("Received None data, possibly due to node deletion")
            return

        # Kiểm tra nếu dữ liệu là dictionary
        if not isinstance(data, dict):
            print(f"Invalid data format received, expected a dictionary: {data}")
            return

        # Đảm bảo các trường cần thiết tồn tại
        required_fields = ['Latitude', 'Longitude', 'AccX', 'AccY', 'AccZ', 'GyroX', 'GyroY', 'GyroZ', 'Temperature']
        if not all(field in data for field in required_fields):
            print(f"Missing required fields in data: {data}")
            return

        # Tạo timestamp thủ công để kiểm tra dữ liệu mới
        current_timestamp = int(time.time() * 1000)  # Timestamp dạng millisecond

        # Bỏ qua nếu timestamp không mới
        if current_timestamp <= last_processed_timestamp:
            print(f"Skipping old timestamp: {current_timestamp}")
            return

        data_point = {
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

        # Chuẩn bị dữ liệu cho dự đoán AI
        features = [
            data_point['AccX'], data_point['AccY'], data_point['AccZ'],
            data_point['GyroX'], data_point['GyroY'], data_point['GyroZ']
        ]
        
        # Sử dụng MotionPredictor để dự đoán rung lắc
        prediction = motion_predictor.predict(features)
        data_point['vibration_detected'] = bool(prediction)

        # In dữ liệu cảm biến và dự đoán
        print(f"\n=== Nhận dữ liệu mới ===")
        print(f"Dữ liệu cảm biến: {json.dumps(data_point, indent=2, ensure_ascii=False)}")
        print(f"Dự đoán rung lắc: {'Có rung' if prediction == 1 else 'Không rung'}")

        # Lưu dữ liệu cảm biến vào SQLite
        SensorData.objects.create(
            AccX=data_point['AccX'],
            AccY=data_point['AccY'],
            AccZ=data_point['AccZ'],
            GyroX=data_point['GyroX'],
            GyroY=data_point['GyroY'],
            GyroZ=data_point['GyroZ'],
            temperature=data_point['Temperature'],
            vibration_detected=data_point['vibration_detected'],
            timestamp=str(current_timestamp)
        )

        # Xử lý cảnh báo rung lắc
        handle_vibration_alert(str(current_timestamp), data_point, prediction)

        # Lưu lộ trình vào SQLite
        if data_point['latitude'] != 0 and data_point['longitude'] != 0:
            Route.objects.create(
                latitude=data_point['latitude'],
                longitude=data_point['longitude'],
                time=str(current_timestamp)  
            )

        # Cập nhật dữ liệu mới nhất và timestamp đã xử lý
        with data_lock:
            global latest_data
            latest_data = data_point
            last_processed_timestamp = current_timestamp

    try:
        ref.listen(callback)
    except Exception as e:
        print(f"Error in Firebase listener: {e}")

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
                return Response({"error": "No data available yet"}, status=status.HTTP_404_NOT_FOUND)
            # Ánh xạ dữ liệu từ latest_data sang định dạng của SensorDataSerializer
            serialized_data = {
                'timestamp': str(last_processed_timestamp),
                'latitude': latest_data['latitude'],
                'longitude': latest_data['longitude'],
                'AccX': latest_data['AccX'],
                'AccY': latest_data['AccY'],
                'AccZ': latest_data['AccZ'],
                'GyroX': latest_data['GyroX'],
                'GyroY': latest_data['GyroY'],
                'GyroZ': latest_data['GyroZ'],
                'Temperature': latest_data['Temperature'],
                'vibration_detected': latest_data['vibration_detected']
            }
            return Response(SensorDataSerializer(serialized_data).data)

class SensorDataHistoryView(APIView):
    def get(self, request):
        # Lấy tham số limit và time_range từ query
        limit = int(request.query_params.get('limit', 50))
        time_range = request.query_params.get('time_range', None)  # time_range dạng millisecond (ví dụ: 3600000 cho 1 giờ)

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
            return Response({"error": "No sensor data found"}, status=status.HTTP_404_NOT_FOUND)

        # Ánh xạ dữ liệu từ model SensorData sang định dạng của SensorDataSerializer
        serialized_data = [
            {
                'timestamp': str(item.timestamp),
                'latitude': 0.0,  # Không có trong model SensorData, để mặc định là 0
                'longitude': 0.0,  # Không có trong model SensorData, để mặc định là 0
                'AccX': item.AccX,
                'AccY': item.AccY,
                'AccZ': item.AccZ,
                'GyroX': item.GyroX,
                'GyroY': item.GyroY,
                'GyroZ': item.GyroZ,
                'Temperature': item.temperature,
                'vibration_detected': item.vibration_detected
            }
            for item in sensor_data
        ]

        return Response({'sensor_data': SensorDataSerializer(serialized_data, many=True).data})

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
            return Response({"error": "No route data found"}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"error": "Alert not found"}, status=status.HTTP_404_NOT_FOUND)
        
# class DeleteSensorDataView(APIView):
#     def delete(self, request):
#         try:
#             count = SensorData.objects.count()
#             SensorData.objects.all().delete()
#             return Response({"message": f"Successfully deleted {count} sensor data records."}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class DeleteRouteDataView(APIView):
#     def delete(self, request):
#         try:
#             count = Route.objects.count()
#             Route.objects.all().delete()
#             return Response({"message": f"Successfully deleted {count} route records."}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class DeleteAlertDataView(APIView):
#     def delete(self, request):
#         try:
#             count = Alert.objects.count()
#             Alert.objects.all().delete()
#             # Đặt lại active_alert về None nếu đang có cảnh báo active
#             global active_alert
#             active_alert = None
#             return Response({"message": f"Successfully deleted {count} alert records."}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)