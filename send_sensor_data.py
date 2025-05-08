import requests
import time
import random

# URL của API Django
URL = "http://172.28.160.1:8000/api/receive-data/"

# Payload mặc định là 0
default_payload = {
    "timestamp": str(int(time.time() * 1000)),
    "latitude": 0.0,
    "longitude": 0.0,
    "AccX": 0.0,
    "AccY": 0.0,
    "AccZ": 0.0,
    "GyroX": 0.0,
    "GyroY": 0.0,
    "GyroZ": 0.0,
    "temperature": 0.0
}

def send_data(payload):
    try:
        response = requests.post(URL, json=payload)
        if response.status_code == 200:
            print("✔️ Data sent successfully:", response.json())
        else:
            print("❌ Failed to send data:", response.text)
    except Exception as e:
        print("❌ Error:", e)

# --- Gửi dữ liệu mặc định ban đầu là 0 ---
print("🚀 Sending default data (all values are 0)...")
send_data(default_payload)
