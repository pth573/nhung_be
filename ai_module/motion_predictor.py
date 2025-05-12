import numpy as np
import joblib
from tensorflow.keras.models import load_model
from pathlib import Path

# Đường dẫn đến thư mục ai_module
BASE_DIR = Path(__file__).resolve().parent

# Load mô hình LSTM và scaler
model = load_model(BASE_DIR / 'lstm_motion_model.h5')
scaler = joblib.load(BASE_DIR / 'scaler.pkl')

# Độ dài chuỗi cho LSTM 
WINDOW_SIZE = 10

class MotionPredictor:
    def __init__(self):
        pass
    
    def predict(self, features):
        """
        Dự đoán rung lắc dựa trên một điểm dữ liệu.
        features: List chứa [AccX, AccY, AccZ, GyroX, GyroY, GyroZ]
        Trả về: 1 (rung lắc) hoặc 0 (không rung lắc)
        """
        # Chuẩn bị dữ liệu cho LSTM
        X_new = np.array([features])  # Chuyển thành mảng 2D
        X_new_scaled = scaler.transform(X_new)  # Chuẩn hóa
        
        # Nhân bản điểm dữ liệu để tạo chuỗi đầu vào có độ dài WINDOW_SIZE
        X_new_seq = np.tile(X_new_scaled, (WINDOW_SIZE, 1))  # Lặp lại để tạo chuỗi thời gian
        X_new_seq = X_new_seq.reshape(1, WINDOW_SIZE, -1)  # Định dạng (1, 10, 6)
        
        # Dự đoán
        y_pred_prob = model.predict(X_new_seq, verbose=0)
        y_pred = (y_pred_prob > 0.5).astype(int)
        return y_pred[0][0]