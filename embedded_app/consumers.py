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
        # Nhận dữ liệu từ client
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