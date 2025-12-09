import sys
import serial
import serial.tools.list_ports
from collections import deque
import time

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QComboBox,
                             QTextEdit, QGridLayout, QGroupBox, QTabWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

# --- THAY ĐỔI: Sử dụng pyqtgraph thay cho matplotlib ---
import pyqtgraph as pg

# Thiết lập mặc định cho pyqtgraph (nền trắng, chữ đen)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class SerialReader(QThread):
    data_received = pyqtSignal(str, str)

    def __init__(self, serial_instance, port_id):
        super().__init__()
        self.serial = serial_instance
        self.port_id = port_id
        self.running = True

    def run(self):
        while self.running and self.serial and self.serial.is_open:
            try:
                line = self.serial.readline().decode('utf-8').strip()
                if line: self.data_received.emit(self.port_id, line)
            except (serial.SerialException, UnicodeDecodeError):
                self.running = False
                break

    def stop(self):
        self.running = False


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.mks_port, self.arduino_port, self.mks_reader, self.arduino_reader = None, None, None, None

        self.DEGREES_PER_TICK = 360.0 / 4096.0
        self.encoder_zero_offset = 0

        self.connection_timer = QTimer(self)
        self.start_time = None
        self.is_any_port_connected = False

        self.max_points = 100
        self.time_data, self.force1_data, self.force2_data, self.total_force_data, self.angle_data = (
        deque(maxlen=self.max_points) for _ in range(5))
        self.time_counter = 0

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Giao diện Điều khiển & Đo lường (pyqtgraph)')
        self.setGeometry(100, 100, 950, 900)
        main_layout = QVBoxLayout()

        # --- Bố cục Giao diện (không đổi) ---
        status_group = QGroupBox("Trạng thái Kết nối & Hoạt động")
        status_layout = QHBoxLayout()
        connection_main_layout = QHBoxLayout()
        mks_connection_group = self.create_connection_group("MKS", 9600)
        arduino_connection_group = self.create_connection_group("Arduino", 115200)
        connection_main_layout.addWidget(mks_connection_group)
        connection_main_layout.addWidget(arduino_connection_group)
        self.timer_label = QLabel("Thời gian hoạt động: 00:00:00")
        self.timer_label.setFont(QFont('Arial', 12, QFont.Bold))
        status_layout.addLayout(connection_main_layout)
        status_layout.addStretch()
        status_layout.addWidget(self.timer_label, alignment=Qt.AlignCenter)
        status_group.setLayout(status_layout)

        self.refresh_button = QPushButton("Làm mới danh sách COM")

        display_layout = QHBoxLayout()
        force_display_group = QGroupBox("Trạng thái Lực Kẹp")
        force_display_layout = QGridLayout()
        self.force1_display_label = QLabel("0.00 N");
        self.force1_display_label.setFont(QFont('Arial', 16, QFont.Bold));
        self.force1_display_label.setStyleSheet("color: #007BFF;")
        self.force2_display_label = QLabel("0.00 N");
        self.force2_display_label.setFont(QFont('Arial', 16, QFont.Bold));
        self.force2_display_label.setStyleSheet("color: #FFC107;")
        self.total_force_display_label = QLabel("0.00 N");
        self.total_force_display_label.setFont(QFont('Arial', 24, QFont.Bold));
        self.total_force_display_label.setStyleSheet("color: #2E8B57;")
        force_display_layout.addWidget(QLabel("Lực Cân 1:"), 0, 0);
        force_display_layout.addWidget(self.force1_display_label, 0, 1)
        force_display_layout.addWidget(QLabel("Lực Cân 2:"), 1, 0);
        force_display_layout.addWidget(self.force2_display_label, 1, 1)
        force_display_layout.addWidget(QLabel("TỔNG LỰC:"), 2, 0);
        force_display_layout.addWidget(self.total_force_display_label, 2, 1)
        force_display_group.setLayout(force_display_layout)

        encoder_display_group = QGroupBox("Trạng thái Encoder & Điều khiển")
        encoder_display_layout = QGridLayout()
        self.encoder_pos_label = QLabel("0");
        self.encoder_pos_label.setFont(QFont('Arial', 14, QFont.Bold));
        self.encoder_pos_label.setStyleSheet("color: #6c757d;")
        self.angle_display_label = QLabel("0.0°");
        self.angle_display_label.setFont(QFont('Arial', 24, QFont.Bold));
        self.angle_display_label.setStyleSheet("color: #B33A3A;")
        self.reset_encoder_button = QPushButton("Đặt Góc Zero (z)");
        self.tare_button_1 = QPushButton("Trừ bì Cân 1 (t)");
        self.tare_button_2 = QPushButton("Trừ bì Cân 2 (u)")
        encoder_display_layout.addWidget(QLabel("Góc Mở:"), 0, 0);
        encoder_display_layout.addWidget(self.angle_display_label, 0, 1)
        encoder_display_layout.addWidget(QLabel("Vị trí thô:"), 1, 0);
        encoder_display_layout.addWidget(self.encoder_pos_label, 1, 1)
        encoder_display_layout.addWidget(self.reset_encoder_button, 0, 2);
        encoder_display_layout.addWidget(self.tare_button_1, 1, 2);
        encoder_display_layout.addWidget(self.tare_button_2, 2, 2)
        encoder_display_group.setLayout(encoder_display_layout)

        display_layout.addWidget(force_display_group)
        display_layout.addWidget(encoder_display_group)

        movement_group = QGroupBox("Điều khiển di chuyển Lên / Xuống (Gửi đến MKS)");
        movement_layout = QGridLayout();
        self.up_button = QPushButton("Lên (u)");
        self.down_button = QPushButton("Xuống (d)");
        self.main_drive_steps_input = QLineEdit("5000");
        self.main_drive_speed_input = QLineEdit("1000")
        movement_layout.addWidget(QLabel("<b>Điều khiển</b>"), 0, 0);
        movement_layout.addWidget(self.up_button, 1, 0);
        movement_layout.addWidget(QLabel("<b>Số bước</b>"), 0, 1);
        movement_layout.addWidget(self.main_drive_steps_input, 1, 1);
        movement_layout.addWidget(QLabel("<b>Tốc độ</b>"), 0, 2);
        movement_layout.addWidget(self.main_drive_speed_input, 1, 2);
        movement_layout.addWidget(self.down_button, 2, 0);
        movement_group.setLayout(movement_layout)
        clamp_group = QGroupBox("Điều khiển Kẹp / Nhả (Trục X - Gửi đến MKS)");
        clamp_layout = QGridLayout();
        self.clamp_button = QPushButton("KẸP (Phải)");
        self.release_button = QPushButton("NHẢ (Trái)");
        self.clamp_steps_input = QLineEdit("1000");
        self.clamp_speed_input = QLineEdit("1600")
        clamp_layout.addWidget(self.clamp_button, 0, 0);
        clamp_layout.addWidget(self.release_button, 1, 0);
        clamp_layout.addWidget(QLabel("Số bước:"), 0, 1);
        clamp_layout.addWidget(self.clamp_steps_input, 0, 2);
        clamp_layout.addWidget(QLabel("Tốc độ:"), 1, 1);
        clamp_layout.addWidget(self.clamp_speed_input, 1, 2);
        clamp_group.setLayout(clamp_layout)
        system_group = QGroupBox("Hệ thống (Gửi đến MKS)");
        system_layout = QHBoxLayout();
        self.enable_button = QPushButton("Bật Motor (e)");
        self.disable_button = QPushButton("Tắt Motor (x)");
        self.stop_button = QPushButton("DỪNG KHẨN CẤP (stop)");
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        system_layout.addWidget(self.enable_button);
        system_layout.addWidget(self.disable_button);
        system_layout.addStretch();
        system_layout.addWidget(self.stop_button);
        system_group.setLayout(system_layout)

        # --- THAY ĐỔI: Tạo và cấu hình các widget đồ thị pyqtgraph ---
        self.tabs = QTabWidget()
        log_group = QGroupBox()
        log_layout = QVBoxLayout()
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        log_layout.addWidget(self.log_console)
        log_group.setLayout(log_layout)

        # Tạo widget đồ thị lực và các đường cong
        self.force_plot_widget = pg.PlotWidget()
        self.force_plot_widget.addLegend()
        self.force_plot_widget.setLabel('left', "Lực (N)")
        self.force_plot_widget.setLabel('bottom', "Mẫu dữ liệu")
        self.force_plot_widget.showGrid(x=True, y=True)
        self.force1_curve = self.force_plot_widget.plot(pen=pg.mkPen('#007BFF', style=Qt.DashLine), name='Lực 1')
        self.force2_curve = self.force_plot_widget.plot(pen=pg.mkPen('#FFC107', style=Qt.DashLine), name='Lực 2')
        self.total_force_curve = self.force_plot_widget.plot(pen=pg.mkPen('#2E8B57', width=2.5), name='Tổng Lực')

        # Tạo widget đồ thị góc và đường cong
        self.angle_plot_widget = pg.PlotWidget()
        self.angle_plot_widget.setLabel('left', "Góc (°)")
        self.angle_plot_widget.setLabel('bottom', "Mẫu dữ liệu")
        self.angle_plot_widget.showGrid(x=True, y=True)
        self.angle_curve = self.angle_plot_widget.plot(pen=pg.mkPen('#B33A3A', width=2))

        self.tabs.addTab(self.force_plot_widget, "📈 Đồ Thị Lực Kẹp")
        self.tabs.addTab(self.angle_plot_widget, "📐 Đồ Thị Góc Mở")
        self.tabs.addTab(log_group, "📟 Log Hệ Thống")

        main_layout.addWidget(status_group);
        main_layout.addWidget(self.refresh_button);
        main_layout.addLayout(display_layout);
        main_layout.addWidget(movement_group);
        main_layout.addWidget(clamp_group);
        main_layout.addWidget(system_group);
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.connect_signals()
        self.refresh_com_ports()

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_com_ports)
        self.mks_connect_button.clicked.connect(lambda: self.connect_port("MKS"))
        self.mks_disconnect_button.clicked.connect(lambda: self.disconnect_port("MKS"))
        self.arduino_connect_button.clicked.connect(lambda: self.connect_port("Arduino"))
        self.arduino_disconnect_button.clicked.connect(lambda: self.disconnect_port("Arduino"))
        self.reset_encoder_button.clicked.connect(self.zero_encoder_angle)
        self.tare_button_1.clicked.connect(lambda: self.send_command("Arduino", 't'))
        self.tare_button_2.clicked.connect(lambda: self.send_command("Arduino", 'u'))
        self.up_button.clicked.connect(lambda: self.send_move_command('u'));
        self.down_button.clicked.connect(lambda: self.send_move_command('d'));
        self.clamp_button.clicked.connect(self.send_clamp_command);
        self.release_button.clicked.connect(self.send_release_command)
        self.enable_button.clicked.connect(lambda: self.send_command("MKS", 'e'));
        self.disable_button.clicked.connect(lambda: self.send_command("MKS", 'x'));
        self.stop_button.clicked.connect(lambda: self.send_command("MKS", 'stop'))
        self.connection_timer.timeout.connect(self.update_timer_display)

    def zero_encoder_angle(self):
        current_pos_str = self.encoder_pos_label.text()
        try:
            self.encoder_zero_offset = int(current_pos_str)
            self.log_console.append(f"HỆ THỐNG: Đã đặt điểm Zero cho góc tại vị trí {self.encoder_zero_offset}.")
        except ValueError:
            self.log_console.append("HỆ THỐNG: Lỗi - Chưa có dữ liệu encoder để đặt Zero.")

    def process_incoming_data(self, port_id, text):
        if port_id == "Arduino":
            try:
                force1_str, force2_str, position_str = text.split(',')
                force1_value, force2_value, encoder_position = float(force1_str), float(force2_str), int(position_str)
                total_force_value = force1_value + force2_value
                relative_position = encoder_position - self.encoder_zero_offset
                relative_angle = relative_position * self.DEGREES_PER_TICK

                self.force1_display_label.setText(f"{force1_value:.2f} N");
                self.force2_display_label.setText(f"{force2_value:.2f} N");
                self.total_force_display_label.setText(f"{total_force_value:.2f} N")
                self.encoder_pos_label.setText(f"{encoder_position}");
                self.angle_display_label.setText(f"{relative_angle:.1f}°")

                self.time_data.append(self.time_counter)
                self.force1_data.append(force1_value)
                self.force2_data.append(force2_value)
                self.total_force_data.append(total_force_value)
                self.angle_data.append(relative_angle)
                self.time_counter += 1
                self.update_graphs()
            except (ValueError, IndexError):
                self.log_console.append(f"ARDUINO < Dữ liệu không hợp lệ: {text}")
        elif port_id == "MKS":
            self.log_console.append(f"MKS < {text}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    # --- THAY ĐỔI: Hàm cập nhật đồ thị dùng pyqtgraph ---
    def update_graphs(self):
        # Chuyển deque sang list để pyqtgraph vẽ
        time_list = list(self.time_data)

        # Cập nhật dữ liệu cho từng đường cong
        self.force1_curve.setData(time_list, list(self.force1_data))
        self.force2_curve.setData(time_list, list(self.force2_data))
        self.total_force_curve.setData(time_list, list(self.total_force_data))

        self.angle_curve.setData(time_list, list(self.angle_data))

    # Các hàm tiện ích (không có thay đổi lớn)
    def create_connection_group(self, port_type, baud_rate):
        group = QGroupBox(f"{port_type} (Baud: {baud_rate})");
        layout = QGridLayout();
        combo = QComboBox();
        connect_button = QPushButton("Kết nối");
        disconnect_button = QPushButton("Ngắt kết nối");
        status_label = QLabel("Chưa kết nối")
        status_label.setStyleSheet("font-weight: bold;");
        layout.addWidget(QLabel("Cổng COM:"), 0, 0);
        layout.addWidget(combo, 0, 1);
        layout.addWidget(connect_button, 1, 0);
        layout.addWidget(disconnect_button, 1, 1);
        layout.addWidget(status_label, 0, 2, 2, 1, Qt.AlignCenter)
        group.setLayout(layout)
        if port_type == "MKS":
            self.mks_com_combo, self.mks_connect_button, self.mks_disconnect_button, self.mks_status_label = combo, connect_button, disconnect_button, status_label
        else:
            self.arduino_com_combo, self.arduino_connect_button, self.arduino_disconnect_button, self.arduino_status_label = combo, connect_button, disconnect_button, status_label
        return group

    def refresh_com_ports(self):
        self.mks_com_combo.clear();
        self.arduino_com_combo.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.mks_com_combo.addItem("Không có"); self.arduino_com_combo.addItem("Không có")
        else:
            for port in ports: self.mks_com_combo.addItem(port.device); self.arduino_com_combo.addItem(port.device)

    def connect_port(self, port_type):
        if port_type == "MKS":
            port_name = self.mks_com_combo.currentText(); baud_rate = 9600
        else:
            port_name = self.arduino_com_combo.currentText(); baud_rate = 115200
        if (port_type == "MKS" and self.mks_port and self.mks_port.is_open) or \
                (port_type == "Arduino" and self.arduino_port and self.arduino_port.is_open): return
        if not port_name or "Không có" in port_name: self.log_console.append(
            f"HỆ THỐNG: Lỗi - Vui lòng chọn cổng COM cho {port_type}."); return
        try:
            port_instance = serial.Serial(port_name, baud_rate, timeout=1)
            self.log_console.append(f"HỆ THỐNG: Đang kết nối {port_type} tới {port_name}...")
            reader_instance = SerialReader(port_instance, port_type);
            reader_instance.data_received.connect(self.process_incoming_data);
            reader_instance.start()
            if port_type == "MKS":
                self.mks_port = port_instance;
                self.mks_reader = reader_instance
                self.mks_status_label.setText("Đã kết nối");
                self.mks_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.arduino_port = port_instance;
                self.arduino_reader = reader_instance
                self.arduino_status_label.setText("Đã kết nối");
                self.arduino_status_label.setStyleSheet("color: green; font-weight: bold;")
            if not self.is_any_port_connected:
                self.start_time = time.time();
                self.connection_timer.start(1000);
                self.is_any_port_connected = True
        except serial.SerialException as e:
            self.log_console.append(f"HỆ THỐNG: Lỗi kết nối {port_type} - {e}")

    def disconnect_port(self, port_type):
        if port_type == "MKS":
            if self.mks_reader: self.mks_reader.stop(); self.mks_reader.wait()
            if self.mks_port and self.mks_port.is_open: self.mks_port.close()
            self.mks_port = None;
            self.mks_status_label.setText("Chưa kết nối");
            self.mks_status_label.setStyleSheet("color: black;")
        else:
            if self.arduino_reader: self.arduino_reader.stop(); self.arduino_reader.wait()
            if self.arduino_port and self.arduino_port.is_open: self.arduino_port.close()
            self.arduino_port = None;
            self.arduino_status_label.setText("Chưa kết nối");
            self.arduino_status_label.setStyleSheet("color: black;")
        self.log_console.append(f"HỆ THỐNG: Đã ngắt kết nối {port_type}.")
        if not (self.mks_port and self.mks_port.is_open) and not (self.arduino_port and self.arduino_port.is_open):
            self.connection_timer.stop();
            self.timer_label.setText("Thời gian hoạt động: 00:00:00");
            self.is_any_port_connected = False

    def update_timer_display(self):
        if self.start_time:
            elapsed_seconds = int(time.time() - self.start_time)
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.setText(f"Thời gian hoạt động: {hours:02}:{minutes:02}:{seconds:02}")

    def send_command(self, port_type, cmd):
        port_to_use = self.mks_port if port_type == "MKS" else self.arduino_port
        if port_to_use and port_to_use.is_open:
            port_to_use.write((cmd + '\n').encode('utf-8')); self.log_console.append(f"GUI > {port_type} > {cmd}")
        else:
            self.log_console.append(f"HỆ THỐNG: Lỗi - Chưa kết nối cổng {port_type}.")

    def send_move_command(self, action):
        self.send_command("MKS", f"{action}:{self.main_drive_steps_input.text()}:{self.main_drive_speed_input.text()}")

    def send_clamp_command(self):
        self.send_command("MKS", f"r:{self.clamp_steps_input.text()}:{self.clamp_speed_input.text()}")

    def send_release_command(self):
        self.send_command("MKS", f"l:{self.clamp_steps_input.text()}:{self.clamp_speed_input.text()}")

    def closeEvent(self, event):
        self.disconnect_port("MKS"); self.disconnect_port("Arduino"); event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())