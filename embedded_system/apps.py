# # embedded_system/apps.py

# from django.apps import AppConfig
# import requests
# import time

# class EmbeddedSystemConfig(AppConfig):
#     name = 'embedded_system'

#     def ready(self):
#         self.call_api_after_start()

#     def call_api_after_start(self):
#         # Địa chỉ API cần gọi
#         url = "http://127.0.0.1:8000/api/receive-data/"  # Cập nhật URL nếu cần

#         # Dữ liệu cần gửi
#         data = {
#             'timestamp': str(int(time.time() * 1000)),
#             'latitude': 0,
#             'longitude': 0,
#             'AccX': 0,
#             'AccY': 0,
#             'AccZ': 0,
#             'GyroX': 0,
#             'GyroY': 0,
#             'GyroZ': 0,
#             'temperature': 0,
#             'vibration_detected': False
#         }

#         # Gửi POST request đến API
#         response = requests.post(url, json=data)

#         if response.status_code == 200:
#             print("API called successfully.")
#         else:
#             print(f"Failed to call API: {response.status_code}")
