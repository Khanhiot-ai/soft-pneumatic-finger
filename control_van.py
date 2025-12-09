import sys
import time
import serial
import serial.tools.list_ports
from collections import deque
import csv
from datetime import datetime
try:
    import filterClass 
except ImportError:
    print("not 'filterClass.py'.")
    class dummyFilter:
        def Work(self, val): return val
    class filterClass: lowPass = dummyFilter

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QLabel, QComboBox, QPushButton, QGroupBox, 
                             QStatusBar, QTextEdit, QSlider, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# --- Cấu hình chung ---
MAX_DATA_POINTS = 100
BAUD_RATE = 115200
LOG_INTERVAL_SECONDS = 11.0 / 17.0

# --- CSS Theme Dark ---
dark_stylesheet = """
    QWidget { background-color: #2E2E2E; color: #E0E0E0; font-family: Segoe UI; font-size: 10pt; }
    QMainWindow, QGroupBox { background-color: #2E2E2E; }
    QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 1ex; font-weight: bold; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
    QPushButton { background-color: #555; border: 1px solid #666; border-radius: 4px; padding: 5px; min-width: 80px; }
    QPushButton:hover { background-color: #6A6A6A; } QPushButton:pressed { background-color: #007ACC; }
    QPushButton:disabled { background-color: #404040; color: #888; }
    QComboBox, QSpinBox { border: 1px solid #555; border-radius: 4px; padding: 3px; background-color: #444; }
    QLabel#pressureLabel { font-size: 14pt; font-weight: bold; color: #00BFFF; }
    QLabel#statusLabel_Connected { color: #4CAF50; font-weight: bold; }
    QLabel#statusLabel_Disconnected { color: #F44336; font-weight: bold; }
    QTextEdit { background-color: #252525; border: 1px solid #555; font-family: Consolas, monaco, monospace; }
    QSlider::groove:horizontal { border: 1px solid #555; height: 8px; background: #444; margin: 2px 0; border-radius: 4px; }
    QSlider::handle:horizontal { background: #007ACC; border: 1px solid #007ACC; width: 18px; margin: -5px 0; border-radius: 9px; }
"""

class SerialWorker(QObject):
    data_received = pyqtSignal(float, float)
    log_message_received = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, port, baudrate):
        super().__init__()
        self.port, self.baudrate, self.serial_connection, self._is_running = port, baudrate, None, True
    def run(self):
        try:
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)
        except serial.SerialException as e:
            self.log_message_received.emit(f"[Lỗi] Không thể mở cổng {self.port}: {e}"); self.finished.emit(); return
        while self._is_running and self.serial_connection and self.serial_connection.is_open:
            try:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if not line: continue
                if line.startswith("ITV1:"):
                    parts = line.split('\t'); p1_str = parts[0].split(':')[1]; p2_str = parts[1].split(':')[1]
                    p1, p2 = float(p1_str), float(p2_str)
                    self.data_received.emit(p1, p2)
                else: self.log_message_received.emit(line)
            except (ValueError, IndexError, serial.SerialException): pass
        if self.serial_connection and self.serial_connection.is_open: self.serial_connection.close()
        self.finished.emit()
    def stop(self): self._is_running = False

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        plt.style.use('dark_background'); fig = Figure(figsize=(5, 4), dpi=100); self.axes = fig.add_subplot(111); super(MplCanvas, self).__init__(fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.pressure1_data, self.pressure2_data = deque([0]*MAX_DATA_POINTS, maxlen=MAX_DATA_POINTS), deque([0]*MAX_DATA_POINTS, maxlen=MAX_DATA_POINTS)
        self.serial_thread, self.serial_worker = None, None
        self.data_file, self.csv_writer = None, None
        self.is_logging, self.last_log_time = False, 0
        self.manual_spinbox1, self.manual_spinbox2 = None, None
        
        filter_order, sampling_time_T, cutoff_frequency = 2, 0.1, 0.5
        self.filter1 = filterClass.lowPass(filter_order, sampling_time_T, cutoff_frequency)
        self.filter2 = filterClass.lowPass(filter_order, sampling_time_T, cutoff_frequency)
        
        self._setup_ui()
        self.update_ports()
        self.setWindowTitle("Chương trình điều khiển Van (v3.0 - Hiệu chuẩn 2 điểm)")
        self.show()

    def _setup_ui(self):
        self.setStyleSheet(dark_stylesheet); main_widget = QWidget(); self.setCentralWidget(main_widget); main_layout = QVBoxLayout(main_widget)
        main_layout.addLayout(self._create_connection_panel())
        self.canvas = MplCanvas(self); self._setup_plot(); main_layout.addWidget(self.canvas)
        main_layout.addLayout(self._create_control_panel())
        self.setStatusBar(QStatusBar(self))
    
    def _create_connection_panel(self):
        layout = QHBoxLayout(); layout.addWidget(QLabel("Cổng COM:")); self.port_combo = QComboBox(); layout.addWidget(self.port_combo)
        self.refresh_button = QPushButton("Làm mới"); self.refresh_button.clicked.connect(self.update_ports); layout.addWidget(self.refresh_button)
        self.connect_button = QPushButton("Kết nối"); self.connect_button.clicked.connect(self.toggle_connection); layout.addWidget(self.connect_button)
        self.connection_status = QLabel("Chưa kết nối"); self.connection_status.setObjectName("statusLabel_Disconnected"); layout.addWidget(self.connection_status)
        layout.addStretch(1); return layout
    
    def _setup_plot(self):
        ax = self.canvas.axes
        self.plot_ref1, = ax.plot(range(MAX_DATA_POINTS), list(self.pressure1_data), 'o-', label='Van 1 - Áp suất', color='#00BFFF', ms=3)
        self.plot_ref2, = ax.plot(range(MAX_DATA_POINTS), list(self.pressure2_data), 'o-', label='Van 2 - Áp suất', color='#FF6347', ms=3)
        ax.set_title("Biểu đồ áp suất thời gian thực"); ax.set_xlabel("Thời gian (mẫu)"); ax.set_ylabel("Áp suất (kPa)")
        ax.legend(); ax.grid(True, ls='--', alpha=0.6); self.canvas.figure.tight_layout()
    
    def _create_control_panel(self):
        layout = QHBoxLayout()
        self.van1_panel, self.pressure_label1, self.manual_spinbox1 = self._create_van_panel(1)
        self.van2_panel, self.pressure_label2, self.manual_spinbox2 = self._create_van_panel(2)
        layout.addWidget(self.van1_panel); layout.addWidget(self.van2_panel)
        layout.addLayout(self._create_right_column(), 1); return layout
    
    def _create_van_panel(self, van_num):
        group = QGroupBox(f"Van {van_num}"); layout = QGridLayout(group)
        layout.addWidget(QLabel("Mở van (%):"), 0, 0)
        manual_slider = QSlider(Qt.Horizontal); manual_slider.setRange(0, 100)
        manual_spinbox = QSpinBox(); manual_spinbox.setRange(0, 100)
        manual_slider.valueChanged.connect(manual_spinbox.setValue); manual_spinbox.valueChanged.connect(manual_slider.setValue)
        layout.addWidget(manual_slider, 1, 0, 1, 2); layout.addWidget(manual_spinbox, 0, 1)
        set_button = QPushButton("Đặt giá trị"); set_button.clicked.connect(lambda: self.set_manual_percentage(van_num, manual_spinbox.value()))
        layout.addWidget(set_button, 2, 0, 1, 2)
        layout.addWidget(QLabel("Áp suất hiện tại:"), 3, 0)
        pressure_label = QLabel("0.0 kPa"); pressure_label.setObjectName("pressureLabel"); layout.addWidget(pressure_label, 3, 1)
        return group, pressure_label, manual_spinbox
    
    def _create_right_column(self):
        layout = QVBoxLayout()
        global_controls_group = QGroupBox("Điều khiển chung"); global_layout = QVBoxLayout(global_controls_group)
        preset_layout = QHBoxLayout(); global_layout.addWidget(QLabel("Đặt nhanh cho cả 2 van:"))
        for percent in [0, 5, 10, 15, 20]:
            btn = QPushButton(f"{percent}%"); btn.clicked.connect(lambda checked, p=percent: self.set_both_vans(p)); preset_layout.addWidget(btn)
        global_layout.addLayout(preset_layout); layout.addWidget(global_controls_group)

        # <<< THAY ĐỔI: Thay thế nút ZERO cũ bằng giao diện hiệu chuẩn 2 điểm >>>
        calib_group = QGroupBox("Hiệu chỉnh (Calibration)"); calib_layout = QGridLayout(calib_group)
        calib_layout.addWidget(QLabel("<b>Bước 1:</b> Ngắt áp suất."), 0, 0, 1, 2)
        btn_v1_zero = QPushButton("Van 1 - Calip Zero"); btn_v1_zero.clicked.connect(lambda: self._send_serial_command("C1,L")); calib_layout.addWidget(btn_v1_zero, 1, 0)
        btn_v2_zero = QPushButton("Van 2 - Calip Zero"); btn_v2_zero.clicked.connect(lambda: self._send_serial_command("C2,L")); calib_layout.addWidget(btn_v2_zero, 1, 1)
        calib_layout.addWidget(QLabel("<b>Bước 2:</b> Cấp áp suất tối đa."), 2, 0, 1, 2)
        btn_v1_max = QPushButton("Van 1 - Calip Max"); btn_v1_max.clicked.connect(lambda: self._send_serial_command("C1,H")); calib_layout.addWidget(btn_v1_max, 3, 0)
        btn_v2_max = QPushButton("Van 2 - Calip Max"); btn_v2_max.clicked.connect(lambda: self._send_serial_command("C2,H")); calib_layout.addWidget(btn_v2_max, 3, 1)
        layout.addWidget(calib_group)

        log_control_group = QGroupBox("Ghi dữ liệu & Log"); log_control_layout = QVBoxLayout(log_control_group)
        self.start_log_button = QPushButton("Bắt đầu ghi"); self.start_log_button.clicked.connect(self.start_logging); self.start_log_button.setEnabled(False); log_control_layout.addWidget(self.start_log_button)
        self.stop_log_button = QPushButton("Dừng ghi"); self.stop_log_button.clicked.connect(self.stop_logging); self.stop_log_button.setEnabled(False); log_control_layout.addWidget(self.stop_log_button)
        self.log_box = QTextEdit(); self.log_box.setReadOnly(True); log_control_layout.addWidget(self.log_box, 1)
        layout.addWidget(log_control_group)
        return layout

    def set_both_vans(self, percentage):
        if self.manual_spinbox1: self.manual_spinbox1.setValue(percentage)
        if self.manual_spinbox2: self.manual_spinbox2.setValue(percentage)
        self.set_manual_percentage(1, percentage); self.set_manual_percentage(2, percentage)
        self.append_log_message(f"--- Đã đặt cả 2 van thành {percentage}% ---")

    def start_logging(self):
        if self.is_logging: self.append_log_message("[Cảnh báo] Đã đang trong quá trình ghi file."); return
        try:
            filename = f"pressure_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.data_file = open(filename, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.data_file); self.csv_writer.writerow(['timestamp', 'pressure_van1', 'pressure_van2'])
            self.is_logging = True; self.start_log_button.setEnabled(False); self.stop_log_button.setEnabled(True)
            self.append_log_message(f"--- Bắt đầu ghi dữ liệu vào file: {filename} ---"); self.last_log_time = time.time() 
        except IOError as e: self.append_log_message(f"[Lỗi] Không thể tạo file log: {e}"); self.is_logging = False

    def stop_logging(self):
        if not self.is_logging: return
        if self.data_file: self.data_file.close(); self.data_file = None; self.csv_writer = None
        self.is_logging = False; self.start_log_button.setEnabled(True); self.stop_log_button.setEnabled(False)
        self.append_log_message("--- Đã dừng ghi và lưu file dữ liệu. ---")

    def toggle_connection(self):
        if self.serial_worker is None:
            port = self.port_combo.currentText()
            if not port or port == "Không tìm thấy": self.append_log_message("[Lỗi] Vui lòng chọn một cổng COM hợp lệ."); return
            self.serial_thread = QThread(); self.serial_worker = SerialWorker(port, BAUD_RATE); self.serial_worker.moveToThread(self.serial_thread)
            self.serial_thread.started.connect(self.serial_worker.run); self.serial_worker.finished.connect(self.on_connection_finished)
            self.serial_worker.data_received.connect(self.update_plot_and_data); self.serial_worker.log_message_received.connect(self.append_log_message)
            self.serial_thread.start()
            self.connect_button.setText("Ngắt kết nối"); self.connection_status.setText(f"Đã kết nối {port}"); self.connection_status.setObjectName("statusLabel_Connected")
            self.log_box.clear(); self.append_log_message(f"--- Bắt đầu phiên làm việc ---")
            self.start_log_button.setEnabled(True); self.stop_log_button.setEnabled(False)
        else:
            if self.serial_worker: self.serial_worker.stop()
        self.connection_status.style().polish(self.connection_status)

    def on_connection_finished(self):
        if self.is_logging: self.stop_logging()
        if self.serial_thread: self.serial_thread.quit(); self.serial_thread.wait()
        self.serial_thread, self.serial_worker = None, None
        self.connect_button.setText("Kết nối"); self.connection_status.setText("Chưa kết nối"); self.connection_status.setObjectName("statusLabel_Disconnected")
        self.connection_status.style().polish(self.connection_status); self.append_log_message("--- Kết nối đã đóng. ---")
        self.start_log_button.setEnabled(False); self.stop_log_button.setEnabled(False)
    
    def update_plot_and_data(self, p1_raw, p2_raw):
        p1_filtered = self.filter1.Work(p1_raw)
        p2_filtered = self.filter2.Work(p2_raw)
        if p1_filtered < 0: p1_filtered = 0.0
        if p2_filtered < 0: p2_filtered = 0.0

        current_time = time.time()
        if self.is_logging and self.csv_writer and (current_time - self.last_log_time >= LOG_INTERVAL_SECONDS):
            self.last_log_time = current_time 
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            self.csv_writer.writerow([timestamp, p1_filtered, p2_filtered])

        self.pressure1_data.append(p1_filtered); self.pressure2_data.append(p2_filtered)
        self.pressure_label1.setText(f"{p1_filtered:.1f} kPa"); self.pressure_label2.setText(f"{p2_filtered:.1f} kPa")
        self.plot_ref1.set_ydata(list(self.pressure1_data)); self.plot_ref2.set_ydata(list(self.pressure2_data))
        
        all_data = list(self.pressure1_data) + list(self.pressure2_data)
        min_val, max_val = (min(all_data) - 5, max(all_data) + 5) if all_data else (-5, 5)
        self.canvas.axes.set_ylim(min(0, min_val), max(10, max_val))
        self.canvas.draw()
    
    def update_ports(self):
        self.port_combo.clear(); ports = [p.device for p in serial.tools.list_ports.comports()]; self.port_combo.addItems(ports if ports else ["Không tìm thấy"])

    def append_log_message(self, message):
        self.log_box.append(message); self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def _send_serial_command(self, command_string):
        if self.serial_worker and self.serial_worker.serial_connection and self.serial_worker.serial_connection.is_open:
            try:
                self.serial_worker.serial_connection.write((command_string + '\n').encode())
                self.append_log_message(f">>> Gửi: {command_string}")
            except serial.SerialException as e: self.append_log_message(f"[LỖI] Không thể gửi: {e}")
        else: self.append_log_message("[Lỗi] Chưa kết nối.")

    def set_manual_percentage(self, van_num, percentage):
        self._send_serial_command(f"P{van_num},{percentage}")
    
    def closeEvent(self, event):
        self.append_log_message("--- Đang đóng ứng dụng... ---")
        if self.is_logging: self.stop_logging()
        if self.serial_worker: self.serial_worker.stop()
        if self.serial_thread: self.serial_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())