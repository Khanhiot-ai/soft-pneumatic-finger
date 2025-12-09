import sys
import time
import serial
import serial.tools.list_ports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QLabel, QComboBox, QPushButton, QDoubleSpinBox,
                             QGroupBox, QStatusBar, QFrame, QTextEdit, QRadioButton,
                             QStackedWidget, QSlider, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# --- Cấu hình giao diện và đồ thị ---
MAX_DATA_POINTS = 100
BAUD_RATE = 115200
dark_stylesheet = """
    QWidget { background-color: #2E2E2E; color: #E0E0E0; font-family: Segoe UI; font-size: 10pt; }
    QMainWindow, QGroupBox { background-color: #2E2E2E; }
    QGroupBox { border: 1px solid #555; border-radius: 5px; margin-top: 1ex; font-weight: bold; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
    QPushButton { background-color: #555; border: 1px solid #666; border-radius: 4px; padding: 5px; min-width: 80px; }
    QPushButton:hover { background-color: #6A6A6A; } QPushButton:pressed { background-color: #007ACC; }
    QComboBox, QDoubleSpinBox, QSpinBox { border: 1px solid #555; border-radius: 4px; padding: 3px; background-color: #444; }
    QLabel#pressureLabel { font-size: 14pt; font-weight: bold; color: #00BFFF; }
    QLabel#statusLabel_Connected { color: #4CAF50; font-weight: bold; }
    QLabel#statusLabel_Disconnected { color: #F44336; font-weight: bold; }
    QTextEdit { background-color: #252525; border: 1px solid #555; font-family: Consolas, monaco, monospace; }
    QSlider::groove:horizontal { border: 1px solid #555; height: 8px; background: #444; margin: 2px 0; border-radius: 4px; }
    QSlider::handle:horizontal { background: #007ACC; border: 1px solid #007ACC; width: 18px; margin: -5px 0; border-radius: 9px; }
"""

# --- Lớp Worker để đọc dữ liệu Serial (Không đổi) ---
class SerialWorker(QObject):
    data_received = pyqtSignal(float, float)
    log_message_received = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, port, baudrate): super().__init__(); self.port, self.baudrate, self.serial_connection, self._is_running = port, baudrate, None, True
    def run(self):
        try: self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1); time.sleep(2)
        except serial.SerialException as e: self.log_message_received.emit(f"[Lỗi] Không thể mở cổng {self.port}: {e}"); self.finished.emit(); return
        while self._is_running and self.serial_connection and self.serial_connection.is_open:
            try:
                line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if not line: continue
                if line.startswith("ITV1:"):
                    parts = line.split('\t'); p1 = float(parts[0][5:]); p2 = float(parts[1][5:]); self.data_received.emit(p1, p2)
                else: self.log_message_received.emit(line)
            except (ValueError, IndexError): self.log_message_received.emit(f"[Lỗi parse] {line}")
        if self.serial_connection and self.serial_connection.is_open: self.serial_connection.close()
        self.finished.emit()
    def stop(self): self._is_running = False

# --- Lớp Matplotlib Canvas (Không đổi) ---
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None): plt.style.use('dark_background'); fig = Figure(figsize=(5,4), dpi=100); self.axes = fig.add_subplot(111); super(MplCanvas, self).__init__(fig)

# --- Cửa sổ chính của ứng dụng ---
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("ITV1030 PID/Manual Control & Monitor")
        self.setGeometry(100, 100, 1300, 800)
        self.time_data = list(range(MAX_DATA_POINTS))
        self.pressure1_data, self.pressure2_data = [0]*MAX_DATA_POINTS, [0]*MAX_DATA_POINTS
        self.setpoint1_data, self.setpoint2_data = [0]*MAX_DATA_POINTS, [0]*MAX_DATA_POINTS
        self.serial_thread, self.serial_worker = None, None
        self.current_setpoint1, self.current_setpoint2 = 0.0, 0.0
        self._setup_ui()
        self.update_ports()
        self.show()

    def _setup_ui(self):
        main_widget = QWidget(); main_layout = QVBoxLayout(main_widget)
        connection_layout = QHBoxLayout(); connection_layout.addWidget(QLabel("Cổng COM:")); self.port_combo = QComboBox(); connection_layout.addWidget(self.port_combo); self.refresh_button = QPushButton("Làm mới"); self.refresh_button.clicked.connect(self.update_ports); connection_layout.addWidget(self.refresh_button); self.connect_button = QPushButton("Kết nối"); self.connect_button.clicked.connect(self.toggle_connection); connection_layout.addWidget(self.connect_button); self.connection_status = QLabel("Chưa kết nối"); self.connection_status.setObjectName("statusLabel_Disconnected"); connection_layout.addWidget(self.connection_status); connection_layout.addStretch(1)
        self.canvas = MplCanvas(self); self.plot_ref1, = self.canvas.axes.plot(self.time_data, self.pressure1_data, 'o-', label='Van 1 - Actual', color='#00BFFF', ms=3); self.plot_setpoint1, = self.canvas.axes.plot(self.time_data, self.setpoint1_data, '--', label='Van 1 - Setpoint', color='#00BFFF', alpha=0.7); self.plot_ref2, = self.canvas.axes.plot(self.time_data, self.pressure2_data, 'o-', label='Van 2 - Actual', color='#FF6347', ms=3); self.plot_setpoint2, = self.canvas.axes.plot(self.time_data, self.setpoint2_data, '--', label='Van 2 - Setpoint', color='#FF6347', alpha=0.7); self.canvas.axes.set_title("Biểu đồ áp suất thời gian thực"); self.canvas.axes.set_xlabel("Thời gian (mẫu)"); self.canvas.axes.set_ylabel("Áp suất (kPa)"); self.canvas.axes.legend(); self.canvas.axes.grid(True, ls='--', alpha=0.6); self.canvas.figure.tight_layout()
        bottom_layout = QHBoxLayout()
        def create_van_panel(van_num):
            group = QGroupBox(f"Van {van_num}"); layout = QGridLayout(group)
            radio_pid = QRadioButton("Tự động (PID)"); radio_manual = QRadioButton("Thủ công (%)"); radio_pid.setChecked(True)
            layout.addWidget(radio_pid, 0, 0); layout.addWidget(radio_manual, 0, 1)
            stacked_widget = QStackedWidget(); layout.addWidget(stacked_widget, 1, 0, 1, 2)
            page_pid = QWidget(); pid_layout = QGridLayout(page_pid); pid_layout.addWidget(QLabel("Áp suất đặt (kPa):"), 0, 0); pid_spinbox = QDoubleSpinBox(); pid_spinbox.setRange(0, 500); pid_spinbox.setDecimals(1); pid_layout.addWidget(pid_spinbox, 0, 1); page_pid.setLayout(pid_layout)
            page_manual = QWidget(); manual_layout = QGridLayout(page_manual); manual_layout.addWidget(QLabel("Mở van (%):"), 0, 0); manual_slider = QSlider(Qt.Horizontal); manual_slider.setRange(0, 100); manual_spinbox = QSpinBox(); manual_spinbox.setRange(0, 100); manual_slider.valueChanged.connect(manual_spinbox.setValue); manual_spinbox.valueChanged.connect(manual_slider.setValue); manual_layout.addWidget(manual_slider, 1, 0, 1, 2); manual_layout.addWidget(manual_spinbox, 0, 1); page_manual.setLayout(manual_layout)
            stacked_widget.addWidget(page_pid); stacked_widget.addWidget(page_manual)
            set_button = QPushButton("Đặt giá trị"); layout.addWidget(set_button, 2, 0, 1, 2); layout.addWidget(QLabel("Áp suất hiện tại:"), 3, 0); pressure_label = QLabel("0.0 kPa"); pressure_label.setObjectName("pressureLabel"); layout.addWidget(pressure_label, 3, 1)
            line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); layout.addWidget(line, 4, 0, 1, 2)
            layout.addWidget(QLabel("<b>PID Tuning</b>"), 5, 0, 1, 2); layout.addWidget(QLabel("Kp:"), 6, 0); kp_box = QDoubleSpinBox(); kp_box.setRange(0, 1000); kp_box.setDecimals(2); kp_box.setValue(20.0); layout.addWidget(kp_box, 6, 1); layout.addWidget(QLabel("Ki:"), 7, 0); ki_box = QDoubleSpinBox(); ki_box.setRange(0, 100); ki_box.setDecimals(2); ki_box.setValue(5.0); layout.addWidget(ki_box, 7, 1); layout.addWidget(QLabel("Kd:"), 8, 0); kd_box = QDoubleSpinBox(); kd_box.setRange(0, 100); kd_box.setDecimals(2); kd_box.setValue(1.0); layout.addWidget(kd_box, 8, 1); tune_button = QPushButton("Gửi Tune"); layout.addWidget(tune_button, 9, 0, 1, 2)
            radio_pid.toggled.connect(lambda checked: self.on_mode_change(van_num, checked, stacked_widget)); tune_button.clicked.connect(lambda: self.send_tune_command(van_num, kp_box.value(), ki_box.value(), kd_box.value()))
            def on_set_button_clicked():
                if radio_pid.isChecked(): self.set_setpoint(van_num, pid_spinbox.value())
                else: self.set_manual_percentage(van_num, manual_spinbox.value())
            set_button.clicked.connect(on_set_button_clicked)
            return group, pressure_label
        van1_panel, self.pressure_label1 = create_van_panel(1); van2_panel, self.pressure_label2 = create_van_panel(2)
        right_column_layout = QVBoxLayout(); global_controls_group = QGroupBox("Điều khiển chung"); global_layout = QVBoxLayout(global_controls_group); self.zero_cal_button = QPushButton("Hiệu chỉnh ZERO (Z)"); self.zero_cal_button.clicked.connect(lambda: self._send_serial_command("Z1")); global_layout.addWidget(self.zero_cal_button); global_layout.addStretch(1); right_column_layout.addWidget(global_controls_group); log_group = QGroupBox("Thông tin từ Van (Log)"); log_layout = QVBoxLayout(log_group); self.log_box = QTextEdit(); self.log_box.setReadOnly(True); log_layout.addWidget(self.log_box); right_column_layout.addWidget(log_group)
        bottom_layout.addWidget(van1_panel); bottom_layout.addWidget(van2_panel); bottom_layout.addLayout(right_column_layout)
        main_layout.addLayout(connection_layout); main_layout.addWidget(self.canvas); main_layout.addLayout(bottom_layout); self.setCentralWidget(main_widget); self.setStatusBar(QStatusBar(self))

    def update_ports(self): self.port_combo.clear(); ports = serial.tools.list_ports.comports(); self.port_combo.addItems([p.device for p in ports] if ports else ["Không tìm thấy"])
    def toggle_connection(self):
        if self.serial_worker is None:
            port = self.port_combo.currentText(); self.serial_thread = QThread(); self.serial_worker = SerialWorker(port, BAUD_RATE); self.serial_worker.moveToThread(self.serial_thread)
            self.serial_thread.started.connect(self.serial_worker.run); self.serial_worker.finished.connect(self.on_connection_finished); self.serial_worker.data_received.connect(self.update_plot); self.serial_worker.log_message_received.connect(self.append_log_message); self.serial_thread.start()
            self.connect_button.setText("Ngắt kết nối"); self.connection_status.setText(f"Đã kết nối {port}"); self.connection_status.setObjectName("statusLabel_Connected"); self.connection_status.style().polish(self.connection_status); self.log_box.clear(); self.append_log_message(f"--- Bắt đầu phiên làm việc ---")
        else:
            if self.serial_worker: self.serial_worker.stop()
    def on_connection_finished(self):
        if self.serial_thread: self.serial_thread.quit(); self.serial_thread.wait()
        self.serial_thread, self.serial_worker = None, None; self.connect_button.setText("Kết nối"); self.connection_status.setText("Chưa kết nối"); self.connection_status.setObjectName("statusLabel_Disconnected"); self.connection_status.style().polish(self.connection_status); self.append_log_message("--- Phiên làm việc kết thúc ---")
    def update_plot(self, p1, p2):
        self.pressure1_data.append(p1); self.pressure1_data.pop(0); self.setpoint1_data.append(self.current_setpoint1); self.setpoint1_data.pop(0)
        self.pressure2_data.append(p2); self.pressure2_data.pop(0); self.setpoint2_data.append(self.current_setpoint2); self.setpoint2_data.pop(0)
        self.pressure_label1.setText(f"{p1:.1f} kPa"); self.pressure_label2.setText(f"{p2:.1f} kPa")
        self.plot_ref1.set_ydata(self.pressure1_data); self.plot_setpoint1.set_ydata(self.setpoint1_data); self.plot_ref2.set_ydata(self.pressure2_data); self.plot_setpoint2.set_ydata(self.setpoint2_data)
        all_data = self.pressure1_data + self.setpoint1_data + self.pressure2_data + self.setpoint2_data
        min_val = min(all_data) - 5 if all_data else -5; max_val = max(all_data) + 5 if all_data else 5
        self.canvas.axes.set_ylim(min(0, min_val), max(10, max_val)); self.canvas.draw()
    def append_log_message(self, message): self.log_box.append(message); self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())
    def _send_serial_command(self, command_string):
        if self.serial_worker and self.serial_worker.serial_connection:
            try: self.serial_worker.serial_connection.write((command_string + '\n').encode()); self.append_log_message(f">>> Gửi: {command_string}")
            except serial.SerialException as e: self.append_log_message(f"[LỖI] Không thể gửi: {e}")
        else: self.append_log_message("[Lỗi] Chưa kết nối.")
    def on_mode_change(self, van_num, is_pid_checked, stacked_widget):
        mode_char = 'A' if is_pid_checked else 'M'
        stacked_widget.setCurrentIndex(0 if is_pid_checked else 1)
        self._send_serial_command(f"M{van_num},{mode_char}")
    def set_setpoint(self, van_num, kpa_value):
        if van_num == 1: self.current_setpoint1 = kpa_value
        else: self.current_setpoint2 = kpa_value
        self._send_serial_command(f"S{van_num},{kpa_value:.1f}")
    def set_manual_percentage(self, van_num, percentage): self._send_serial_command(f"P{van_num},{percentage}")
    def send_tune_command(self, van_num, kp, ki, kd): self._send_serial_command(f"T{van_num},{kp:.2f},{ki:.2f},{kd:.2f}")
    def closeEvent(self, event):
        if self.serial_worker: self.serial_worker.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(dark_stylesheet)
    window = MainWindow()
    sys.exit(app.exec_())