# # sensors/consumers.py
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer
# from channels.layers import get_channel_layer

# class SensorDataConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_group_name = 'sensor_data_group'
#         # Tham gia vào nhóm WebSocket
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#         await self.accept()

#     async def disconnect(self, close_code):
#         # Rời nhóm WebSocket
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         # Xử lý dữ liệu nhận từ client (nếu cần)
#         pass

#     async def send_sensor_data(self, event):
#         data = event['data']
#         # Gửi dữ liệu tới WebSocket
#         await self.send(text_data=json.dumps({
#             'type': 'sensor_data',
#             'data': data
#         }))




# # consumers.py
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class SensorDataConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = "sensor_data"
#         self.room_group_name = f"sensor_{self.room_name}"

#         # Tham gia vào nhóm WebSocket
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         # Gửi tin nhắn xác nhận khi kết nối thành công
#         await self.send(text_data=json.dumps({
#             'message': 'Connection established'
#         }))

#     async def disconnect(self, close_code):
#         # Rời khỏi nhóm khi kết nối bị ngắt
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         # Nhận dữ liệu từ client và trả lời lại
#         data = json.loads(text_data)
#         await self.send(text_data=json.dumps({
#             'message': f"Received: {data}"
#         }))

#     async def send_sensor_data(self, event):
#         # Gửi dữ liệu lên client
#         message = event['message']
#         await self.send(text_data=json.dumps({
#             'message': message
#         }))



# OK1
# # consumers.py
# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class SensorDataConsumer(AsyncWebsocketConsumer):

#     async def disconnect(self, close_code):
#         # Rời khỏi nhóm khi kết nối bị ngắt
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     async def receive(self, text_data):
#         # Nhận dữ liệu từ client và trả lời lại
#         data = json.loads(text_data)
#         await self.send(text_data=json.dumps({
#             'message': f"Received: {data}"
#         }))

#     async def send_sensor_data(self, event):
#         if not self.accepted:
#             print("Không thể gửi dữ liệu, kết nối WebSocket chưa được chấp nhận")
#             return

#         # Gửi dữ liệu nếu kết nối đã thành công
#         await self.send(text_data=json.dumps({
#             'message': 'Dữ liệu từ server'
#         }))

# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SensorDataConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_group_name = "sensor_data_group"  # Tên group mà client sẽ join vào
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Khi client ngắt kết nối, nó sẽ rời khỏi group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Nhận dữ liệu từ client (nếu cần)
        data = json.loads(text_data)
        await self.send(text_data=json.dumps({
            'message': f"Received: {data}"
        }))


    async def send_sensor_data(self, event):
        sensor_data = event["data"]

        print("Sending sensor data to WebSocket clients")
        print(f"Data: {sensor_data}")

        await self.send(text_data=json.dumps({
            'message': 'Dữ liệu từ server:',
            'data': sensor_data
        }))

    # async def send_sensor_data(self, event):
    #     print("OKkkkk")
    #     # Dữ liệu mà bạn muốn gửi lên client
        # sensor_data = {
        #     "timestamp": "1746449248646",
        #     "latitude": 5.0,
        #     "longitude": 10.0,
        #     "AccX": 15.1,
        #     "AccY": 17.39627,
        #     "AccZ": 16.54872,
        #     "GyroX": -1.29516,
        #     "GyroY": -6.53541,
        #     "GyroZ": 11.4,
        #     "temperature": -23.60823,
        #     "vibration_detected": True
        # }

    #     print("Sending sensor data to WebSocket clients")
    #     print(f"Data: {sensor_data}")

    #     # Gửi dữ liệu này lên WebSocket client
    #     await self.send(text_data=json.dumps({
    #         'message': 'Gui du lieu tu server:',
    #         'data': sensor_data  # Dữ liệu từ server gửi lên client
    #     }))



#them 2
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

class AlertConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'alerts'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'alert_message',
                'message': message
            }
        )

    async def alert_message(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'message': message
        }))


class RecentRouteConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'recent_route'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        route_info = data.get('route_info', '')
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'route_info_message',
                'route_info': route_info
            }
        )

    async def route_info_message(self, event):
        route_info = event['route_info']
        await self.send(text_data=json.dumps({
            'route_info': route_info
        }))