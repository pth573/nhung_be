from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from firebase_admin import db
import requests
from .models import Route, Alert, SensorData, Trip, DeviceToken
from .serializers import SensorDataSerializer, RouteSerializer, AlertSerializer, TripSerializer, DeviceTokenSerializer
import threading
from ai_module.motion_predictor import MotionPredictor
import json
import time
from datetime import datetime, timedelta
from geopy.distance import geodesic
from django.db.models import Q
from firebase_admin import messaging

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
                location=get_address_from_nominatim(new_data['latitude'], new_data['longitude']),
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
        latitude = data['latitude']
        longitude = data['longitude']
        address = get_address_from_nominatim(latitude, longitude)
        send_push_notification("Cảnh báo rung lắc", f"Phát hiện rung lắc tại {address}")

        if active_alert is None:
            active_alert = Alert.objects.create(
                start_time=timestamp,
                end_time=None,
                latitude=data['latitude'],
                longitude=data['longitude'],
                location=address,
                is_active=True
            )
    elif prediction == 0 and active_alert is not None:
        active_alert.end_time = timestamp
        active_alert.is_active = False
        active_alert.save()
        active_alert = None

def send_push_notification(title, body):
    try:
        token = DeviceToken.objects.first() 
        print(f"Token: {token}")
        if token:
            # Tạo thông báo
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                token=token.token,
            )

            response = messaging.send(message)
            print(f'Successfully sent message: {response}')
        else:
            print("No token found for this user.")

    except Exception as e:
        print(f'Error sending message: {e}')

def get_address_from_nominatim(latitude, longitude):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('display_name', '-')
        return '-'
    except Exception as e:
        print(f"Nominatim error: {e}")
        return '-'

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
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 10))
        order = request.query_params.get('order', 'desc')  # 'asc' hoặc 'desc'
        query = request.query_params.get('query', '')

        alerts = Alert.objects.all()

       # Lọc theo location nếu có query
        if query:
            alerts = alerts.filter(location__icontains=query)

        # Sắp xếp theo thời gian
        if order == 'asc':
            alerts = alerts.order_by('start_time')
        else:
            alerts = alerts.order_by('-start_time')

        # Phân trang
        alerts = alerts[offset:offset + limit]

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
        
#Trip
class StartTripView(APIView):
    def post(self, request):
        latest_route = Route.objects.order_by('-time').first()
        if not latest_route:
            return Response({"message": f"Start trip"}, status=status.HTTP_404_NOT_FOUND)
        
        trip = Trip.objects.create(start_route=latest_route)
        return Response(TripSerializer(trip).data, status=status.HTTP_201_CREATED)

class EndTripView(APIView):
    def post(self, request):
        trip = Trip.objects.filter(end_route__isnull=True).order_by('-id').first()
        if not trip:
            return Response({'error': 'No active trip found'}, status=status.HTTP_404_NOT_FOUND)

        end_route = Route.objects.order_by('-time').first()
        if not end_route:
            return Response({'error': 'No route data available'}, status=status.HTTP_404_NOT_FOUND)

        trip.end_route = end_route

        # Tính khoảng cách
        start_coords = (trip.start_route.latitude, trip.start_route.longitude)
        end_coords = (end_route.latitude, end_route.longitude)
        trip.distance = geodesic(start_coords, end_coords).km

        # Tính duration từ time dạng epoch (ms)
        try:
            start_time = datetime.fromtimestamp(int(trip.start_route.time) / 1000)
            end_time = datetime.fromtimestamp(int(end_route.time) / 1000)
            trip.duration = end_time - start_time
        except Exception:
            trip.duration = None

        trip.save()
        return Response({"message": f"End trip"}, status=status.HTTP_200_OK)

class TripView(APIView):
    def get(self, request):
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', 10))
        order = request.query_params.get('order', 'desc')  # asc / desc
        query = request.query_params.get('query', '') 

        trips = Trip.objects.all()

        # Query
        if query:
            trips = trips.filter(
                Q(start_route__location=query) |
                Q(end_route__location=query) 
            )

        # Sắp xếp theo duration (nếu có), hoặc theo id
        if order == 'asc':
            trips = trips.order_by('id')
        else:
            trips = trips.order_by('-id')

        # Phân trang
        trips = trips[offset:offset + limit]

        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

class DeviceTokenView(APIView):
    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        print(serializer)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            DeviceToken.objects.update_or_create(token=token)
            return Response({'message': 'Token saved'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class NotificationView(APIView):
    def post(self, request):
        title = 'Test Notification'
        body = 'This is a test notification.'
        
        try:
            send_push_notification(title, body)
            return Response({'message': 'Notification sent successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)










# sensors/views.py
from django.http import JsonResponse
from .utils import send_sensor_data_to_ws, send_alert_to_ws, send_recent_route_to_ws

def get_current_sensor_data(request):
    # Giả sử lấy dữ liệu sensor từ một nguồn
    data = {'sensor1': 30, 'sensor2': 45}
    send_sensor_data_to_ws(data)
    return JsonResponse({'status': 'success', 'data': data})

def get_alerts(request):
    alerts = {'alert1': 'Warning: High temperature'}
    send_alert_to_ws(alerts)
    return JsonResponse({'status': 'success', 'alerts': alerts})

def get_recent_route(request):
    route = {'route1': 'A->B->C'}
    send_recent_route_to_ws(route)
    return JsonResponse({'status': 'success', 'route': route})


# views.py hoặc bất kỳ nơi nào trong project của bạn
from channels.layers import get_channel_layer

def send_test_data():
    channel_layer = get_channel_layer()

    # Dữ liệu bạn muốn gửi
    sensor_data = "Test sensor data"

    # Gửi dữ liệu đến tất cả các client trong nhóm "sensor_data"
    channel_layer.group_send(
        "sensor_sensor_data",  # Nhóm (group) mà các client tham gia
        {
            'type': 'send_sensor_data',  # Phương thức sẽ được gọi trong consumer
            'message': sensor_data  # Dữ liệu bạn muốn gửi
        }
    )


# views.py
from django.http import JsonResponse
def trigger_send_data(request):
    print("OK1")
    send_test_data()
    return JsonResponse({"status": "Data sent to WebSocket"})



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class SendDataView(APIView):
    def post(self, request):
        # Get the channel layer and group name
        channel_layer = get_channel_layer()
        group_name = "sensor_data_group"

        print("OK1")
        # Gửi message đến group thông qua async_to_sync
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_sensor_data',
                'message': 'send_data'
            }
        )

        print("OK2")
        return Response({"message": "Sensor data sent to WebSocket clients."}, status=status.HTTP_200_OK)

    
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync

# channel_layer = get_channel_layer()

# # Gửi dữ liệu đến group mà các client WebSocket đang join
# async_to_sync(channel_layer.group_send)(
#     "sensor_data_group",  # Tên của group trong consumer
#     {
#         "type": "send_sensor_data",  # Gọi hàm send_sensor_data trong consumer
#         "message": "Dữ liệu cảm biến từ server"  # Bạn có thể gửi thêm thông tin nếu cần
#     }
# )



from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import time
import json
from .models import SensorData, Route

@csrf_exempt
def receive_sensor_data(request):
    if request.method == 'POST':
        try:
            # Nhận và giải mã dữ liệu JSON từ body của request
            body = json.loads(request.body)

            # Chuẩn hóa dữ liệu với các giá trị mặc định nếu không có trong request
            sensor_data = {
                'timestamp': body.get('timestamp', str(int(time.time() * 1000))),
                'latitude': body.get('latitude', 0),
                'longitude': body.get('longitude', 0),
                'AccX': body.get('AccX', 0),
                'AccY': body.get('AccY', 0),
                'AccZ': body.get('AccZ', 0),
                'GyroX': body.get('GyroX', 0),
                'GyroY': body.get('GyroY', 0),
                'GyroZ': body.get('GyroZ', 0),
                'temperature': body.get('temperature', 0),
                'vibration_detected': body.get('vibration_detected', False)
            }

            # Tạo danh sách các đặc trưng cho mô hình dự đoán
            features = [
                sensor_data['AccX'], sensor_data['AccY'], sensor_data['AccZ'],
                sensor_data['GyroX'], sensor_data['GyroY'], sensor_data['GyroZ']
            ]

            # Dự đoán rung lắc từ dữ liệu cảm biến
            prediction = motion_predictor.predict(features)
            sensor_data['vibration_detected'] = bool(prediction)

            # Lưu dữ liệu cảm biến vào cơ sở dữ liệu
            SensorData.objects.create(
                latitude=sensor_data['latitude'],
                longitude=sensor_data['longitude'],
                AccX=sensor_data['AccX'],
                AccY=sensor_data['AccY'],
                AccZ=sensor_data['AccZ'],
                GyroX=sensor_data['GyroX'],
                GyroY=sensor_data['GyroY'],
                GyroZ=sensor_data['GyroZ'],
                temperature=sensor_data['temperature'],
                vibration_detected=sensor_data['vibration_detected'],
                timestamp=sensor_data['timestamp']
            )

            print(f"Dữ liệu cảm biến: {sensor_data}")

            # Xử lý cảnh báo rung lắc
            current_timestamp = int(time.time() * 1000)  # Cập nhật lại timestamp
            handle_vibration_alert(str(current_timestamp), sensor_data, prediction)

            # Lưu lộ trình vào SQLite nếu có tọa độ hợp lệ
            if sensor_data['latitude'] != 0 and sensor_data['longitude'] != 0:
                location = get_address_from_nominatim(sensor_data['latitude'], sensor_data['longitude'])
                Route.objects.create(
                    latitude=sensor_data['latitude'],
                    longitude=sensor_data['longitude'],
                    location=location,
                    time=str(current_timestamp)
                )

            # Cập nhật dữ liệu mới nhất vào bộ nhớ (giả sử data_lock là một đối tượng đồng bộ)
            with data_lock:
                global latest_data
                latest_data = sensor_data
                last_processed_timestamp = current_timestamp

            # Gửi dữ liệu sang WebSocket client
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "sensor_data_group",  # Nhóm đã join từ WebSocket consumer
                {
                    'type': 'send_sensor_data',  # Loại sự kiện
                    'data': sensor_data  # Dữ liệu gửi đến WebSocket client
                }
            )

            # Trả về phản hồi thành công
            return JsonResponse({'status': 'success', 'prediction': int(prediction)})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format'}, status=400)
        except KeyError as e:
            return JsonResponse({'status': 'error', 'message': f'Missing key: {str(e)}'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'only POST accepted'}, status=405)




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class HiView(APIView):
    def post(self, request):
        message = request.data.get('message')
        if message:
            return Response({'message': message}, status=status.HTTP_200_OK)
        return Response({'error': 'Missing message field'}, status=status.HTTP_400_BAD_REQUEST)
