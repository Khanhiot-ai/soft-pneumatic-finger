import sys
import serial
import serial.tools.list_ports
from collections import deque
import math
import csv
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QComboBox,

                             QTextEdit, QGridLayout, QGroupBox, QTabWidget)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

import matplotlib

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


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
        self.MM_PER_TICK = 0.02756  # Hằng số hiệu chuẩn khoảng cách
        self.DISTANCE_CALIBRATION_OFFSET = 16.0  # ### <<< THAY ĐỔI: Thêm hằng số hiệu chuẩn kẹp (mm)

        self.is_recording = False
        self.recorded_data = []

        self.max_points = 100
        self.time_data = deque(maxlen=self.max_points)
        self.force1_data = deque(maxlen=self.max_points)
        self.force2_data = deque(maxlen=self.max_points)
        self.total_force_data = deque(maxlen=self.max_points)
        self.angle_data = deque(maxlen=self.max_points)
        self.distance_data = deque(maxlen=self.max_points)
        self.time_counter = 0

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Giao diện Điều khiển & Đo lường Chi tiết')
        self.setGeometry(100, 100, 950, 900)
        main_layout = QVBoxLayout()
        connection_main_layout = QHBoxLayout()
        mks_connection_group = self.create_connection_group("MKS", 9600)
        arduino_connection_group = self.create_connection_group("Arduino", 115200)
        connection_main_layout.addWidget(mks_connection_group)
        connection_main_layout.addWidget(arduino_connection_group)
        self.refresh_button = QPushButton("Làm mới danh sách COM")
        display_layout = QHBoxLayout()
        force_display_group = QGroupBox("Trạng thái Lực Kẹp")
        force_display_layout = QGridLayout()
        self.force1_display_label = QLabel("0.00 N")
        self.force1_display_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.force1_display_label.setStyleSheet("color: #007BFF;")
        self.force2_display_label = QLabel("0.00 N")
        self.force2_display_label.setFont(QFont('Arial', 16, QFont.Bold))
        self.force2_display_label.setStyleSheet("color: #FFC107;")
        self.total_force_display_label = QLabel("0.00 N")
        self.total_force_display_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.total_force_display_label.setStyleSheet("color: #2E8B57;")
        force_display_layout.addWidget(QLabel("Lực Cân 1:"), 0, 0)
        force_display_layout.addWidget(self.force1_display_label, 0, 1)
        force_display_layout.addWidget(QLabel("Lực Cân 2:"), 1, 0)
        force_display_layout.addWidget(self.force2_display_label, 1, 1)
        force_display_layout.addWidget(QLabel("TỔNG LỰC:"), 2, 0)
        force_display_layout.addWidget(self.total_force_display_label, 2, 1)
        force_display_group.setLayout(force_display_layout)
        encoder_display_group = QGroupBox("Trạng thái Encoder & Điều khiển")
        encoder_display_layout = QGridLayout()
        self.encoder_pos_label = QLabel("0")
        self.encoder_pos_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.encoder_pos_label.setStyleSheet("color: #6c757d;")
        self.angle_display_label = QLabel("0.0°")
        self.angle_display_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.angle_display_label.setStyleSheet("color: #B33A3A;")
        self.distance_display_label = QLabel("0.00 mm")
        self.distance_display_label.setFont(QFont('Arial', 24, QFont.Bold))
        self.distance_display_label.setStyleSheet("color: #4B0082;")
        self.reset_encoder_button = QPushButton("Đặt Góc Zero (z)")
        self.tare_button_1 = QPushButton("Trừ bì Cân 1 (t)")
        self.tare_button_2 = QPushButton("Trừ bì Cân 2 (u)")
        encoder_display_layout.addWidget(QLabel("Khoảng cách mở:"), 0, 0)
        encoder_display_layout.addWidget(self.distance_display_label, 0, 1)
        encoder_display_layout.addWidget(QLabel("Góc Mở:"), 1, 0)
        encoder_display_layout.addWidget(self.angle_display_label, 1, 1)
        encoder_display_layout.addWidget(QLabel("Vị trí thô:"), 2, 0)
        encoder_display_layout.addWidget(self.encoder_pos_label, 2, 1)
        encoder_display_layout.addWidget(self.reset_encoder_button, 0, 2)
        encoder_display_layout.addWidget(self.tare_button_1, 1, 2)
        encoder_display_layout.addWidget(self.tare_button_2, 2, 2)
        encoder_display_group.setLayout(encoder_display_layout)
        display_layout.addWidget(force_display_group)
        display_layout.addWidget(encoder_display_group)
        movement_group = QGroupBox("Điều khiển di chuyển Lên / Xuống (Gửi đến MKS)")
        movement_layout = QGridLayout()
        self.up_button = QPushButton("Lên (u)")
        self.down_button = QPushButton("Xuống (d)")
        self.main_drive_steps_input = QLineEdit("5000")
        self.main_drive_speed_input = QLineEdit("1000")
        movement_layout.addWidget(QLabel("<b>Điều khiển</b>"), 0, 0)
        movement_layout.addWidget(self.up_button, 1, 0)
        movement_layout.addWidget(QLabel("<b>Số bước</b>"), 0, 1)
        movement_layout.addWidget(self.main_drive_steps_input, 1, 1)
        movement_layout.addWidget(QLabel("<b>Tốc độ</b>"), 0, 2)
        movement_layout.addWidget(self.main_drive_speed_input, 1, 2)
        movement_layout.addWidget(self.down_button, 2, 0)
        movement_group.setLayout(movement_layout)
        clamp_group = QGroupBox("Điều khiển Kẹp / Nhả (Trục X - Gửi đến MKS)")
        clamp_layout = QGridLayout()
        self.clamp_button = QPushButton("NHẢ (Phải)")
        self.release_button = QPushButton("KẸP (Trái)")
        self.clamp_steps_input = QLineEdit("100")
        self.clamp_speed_input = QLineEdit("5000")
        clamp_layout.addWidget(self.clamp_button, 0, 0)
        clamp_layout.addWidget(self.release_button, 1, 0)
        clamp_layout.addWidget(QLabel("Số bước:"), 0, 1)
        clamp_layout.addWidget(self.clamp_steps_input, 0, 2)
        clamp_layout.addWidget(QLabel("Tốc độ:"), 1, 1)
        clamp_layout.addWidget(self.clamp_speed_input, 1, 2)
        clamp_group.setLayout(clamp_layout)
        system_group = QGroupBox("Hệ thống (Gửi đến MKS)")
        system_layout = QHBoxLayout()
        self.enable_button = QPushButton("Bật Motor (e)")
        self.disable_button = QPushButton("Tắt Motor (x)")
        self.stop_button = QPushButton("DỪNG KHẨN CẤP (stop)")
        self.stop_button.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        system_layout.addWidget(self.enable_button)
        system_layout.addWidget(self.disable_button)
        system_layout.addStretch()
        system_layout.addWidget(self.stop_button)
        system_group.setLayout(system_layout)

        record_group = QGroupBox("Ghi dữ liệu Thí nghiệm")
        record_layout = QHBoxLayout()
        self.start_record_button = QPushButton("Bắt đầu Ghi")
        self.stop_record_button = QPushButton("Dừng Ghi & Lưu File")
        self.stop_record_button.setEnabled(False)
        self.record_status_label = QLabel("Trạng thái: Chưa ghi")
        self.record_status_label.setFont(QFont('Arial', 10, QFont.Bold))
        record_layout.addWidget(self.start_record_button)
        record_layout.addWidget(self.stop_record_button)
        record_layout.addStretch()
        record_layout.addWidget(self.record_status_label)
        record_group.setLayout(record_layout)

        self.tabs = QTabWidget()
        log_group = QGroupBox()
        log_layout = QVBoxLayout()
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        log_layout.addWidget(self.log_console)
        log_group.setLayout(log_layout)
        force_graph_widget = self.create_graph_widget("force")
        angle_graph_widget = self.create_graph_widget("angle")
        self.tabs.addTab(force_graph_widget, "📈 Đồ Thị Lực Kẹp")
        self.tabs.addTab(angle_graph_widget, "📐 Đồ Thị Góc & Khoảng cách")
        self.tabs.addTab(log_group, "📟 Log Hệ Thống")

        main_layout.addLayout(connection_main_layout)
        main_layout.addWidget(self.refresh_button)
        main_layout.addLayout(display_layout)
        main_layout.addWidget(movement_group)
        main_layout.addWidget(clamp_group)
        main_layout.addWidget(system_group)
        main_layout.addWidget(record_group)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
        self.connect_signals()
        self.refresh_com_ports()

    def create_graph_widget(self, graph_type):
        widget = QWidget()
        layout = QVBoxLayout()
        figure = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(figure)

        ax = figure.add_subplot(111)

        if graph_type == "force":
            self.force_ax = ax
            self.force_canvas = canvas
            ax.set_title("Lực Kẹp Theo Thời Gian")
            ax.set_ylabel("Lực (N)")

        elif graph_type == "angle":
            self.angle_ax = ax
            self.angle_canvas = canvas
            ax.set_title("Góc & Khoảng cách Mở")
            ax.set_ylabel("Góc (°)", color='#B33A3A')
            self.distance_ax = self.angle_ax.twinx()
            self.distance_ax.set_ylabel("Khoảng cách (mm)", color='#4B0082')

        ax.set_xlabel("Mẫu dữ liệu")
        ax.grid(True)

        toolbar = NavigationToolbar(canvas, self)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        widget.setLayout(layout)
        return widget

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_com_ports)
        self.mks_connect_button.clicked.connect(lambda: self.connect_port("MKS"))
        self.mks_disconnect_button.clicked.connect(lambda: self.disconnect_port("MKS"))
        self.arduino_connect_button.clicked.connect(lambda: self.connect_port("Arduino"))
        self.arduino_disconnect_button.clicked.connect(lambda: self.disconnect_port("Arduino"))
        self.reset_encoder_button.clicked.connect(self.zero_encoder_angle)
        self.tare_button_1.clicked.connect(lambda: self.send_command("Arduino", 't'))
        self.tare_button_2.clicked.connect(lambda: self.send_command("Arduino", 'u'))
        self.up_button.clicked.connect(lambda: self.send_move_command('u'))
        self.down_button.clicked.connect(lambda: self.send_move_command('d'))
        self.clamp_button.clicked.connect(self.send_clamp_command)
        self.release_button.clicked.connect(self.send_release_command)
        self.enable_button.clicked.connect(lambda: self.send_command("MKS", 'e'))
        self.disable_button.clicked.connect(lambda: self.send_command("MKS", 'x'))
        self.stop_button.clicked.connect(lambda: self.send_command("MKS", 'stop'))
        self.start_record_button.clicked.connect(self.start_recording)
        self.stop_record_button.clicked.connect(self.stop_recording)

    def start_recording(self):
        if self.is_recording:
            return
        self.recorded_data = []
        header = ['Timestamp', 'Luc_Can_1 (N)', 'Luc_Can_2 (N)', 'Tong_Luc (N)', 'Vi_tri_tho_Encoder', 'Goc_Mo (do)',
                  'Khoang_cach_Mo (mm)']
        self.recorded_data.append(header)

        self.is_recording = True
        self.record_status_label.setText("Trạng thái: Đang ghi...")
        self.record_status_label.setStyleSheet("color: red; font-weight: bold;")
        self.start_record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)
        self.log_console.append("HỆ THỐNG: Bắt đầu ghi dữ liệu thí nghiệm.")

    def stop_recording(self):
        if not self.is_recording:
            return
        self.is_recording = False
        self.record_status_label.setText("Trạng thái: Dừng & Đang lưu...")
        self.record_status_label.setStyleSheet("color: black; font-weight: bold;")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"data_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(self.recorded_data)
            self.log_console.append(
                f"HỆ THỐNG: Đã lưu thành công {len(self.recorded_data) - 1} dòng dữ liệu vào file {filename}")
        except Exception as e:
            self.log_console.append(f"HỆ THỐNG: Lỗi! Không thể lưu file. Lý do: {e}")

        self.record_status_label.setText("Trạng thái: Chưa ghi")
        self.start_record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)

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
                force1_value = float(force1_str)
                force2_value = float(force2_str)
                encoder_position = int(position_str)
                total_force_value = force1_value + force2_value
                relative_position = self.encoder_zero_offset - encoder_position
                relative_angle = relative_position * self.DEGREES_PER_TICK

                # ### <<< THAY ĐỔI: Cộng thêm 16mm vào kết quả cuối cùng
                opening_distance = (abs(relative_position) * self.MM_PER_TICK) + self.DISTANCE_CALIBRATION_OFFSET

                self.force1_display_label.setText(f"{force1_value:.2f} N")
                self.force2_display_label.setText(f"{force2_value:.2f} N")
                self.total_force_display_label.setText(f"{total_force_value:.2f} N")
                self.encoder_pos_label.setText(f"{encoder_position}")
                self.angle_display_label.setText(f"{relative_angle:.1f}°")
                self.distance_display_label.setText(f"{opening_distance:.2f} mm")

                self.time_data.append(self.time_counter)
                self.force1_data.append(force1_value)
                self.force2_data.append(force2_value)
                self.total_force_data.append(total_force_value)
                self.angle_data.append(relative_angle)
                self.distance_data.append(opening_distance)
                self.time_counter += 1
                self.update_graphs()

                if self.is_recording:
                    current_data_row = [
                        datetime.now().strftime('%H:%M:%S.%f')[:-3],
                        f"{force1_value:.3f}",
                        f"{force2_value:.3f}",
                        f"{total_force_value:.3f}",
                        encoder_position,
                        f"{relative_angle:.2f}",
                        f"{opening_distance:.3f}"
                    ]
                    self.recorded_data.append(current_data_row)

            except (ValueError, IndexError):
                self.log_console.append(f"ARDUINO < Dữ liệu không hợp lệ: {text}")
        elif port_id == "MKS":
            self.log_console.append(f"MKS < {text}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def update_graphs(self):
        self.force_ax.clear()
        self.force_ax.plot(self.time_data, self.force1_data, marker='.', linestyle='-', color='#007BFF', label='Lực 1')
        self.force_ax.plot(self.time_data, self.force2_data, marker='.', linestyle='-', color='#FFC107', label='Lực 2')
        self.force_ax.plot(self.time_data, self.total_force_data, marker='.', linestyle='-', color='#2E8B57',
                           label='Tổng Lực', linewidth=2.0)
        self.force_ax.set_title("Lực Kẹp Theo Thời Gian")
        self.force_ax.set_xlabel("Mẫu dữ liệu")
        self.force_ax.set_ylabel("Lực (N)")
        self.force_ax.grid(True)
        self.force_ax.legend()
        self.force_canvas.draw()

        self.angle_ax.clear()
        self.distance_ax.clear()
        self.angle_ax.plot(self.time_data, self.angle_data, marker='.', linestyle='-', color='#B33A3A', label='Góc mở')
        self.distance_ax.plot(self.time_data, self.distance_data, marker='.', linestyle='-', color='#4B0082',
                              label='Khoảng cách')
        self.angle_ax.set_title("Góc & Khoảng cách Mở")
        self.angle_ax.set_xlabel("Mẫu dữ liệu")
        self.angle_ax.set_ylabel("Góc (°)", color='#B33A3A')
        self.distance_ax.set_ylabel("Khoảng cách (mm)", color='#4B0082')
        self.angle_ax.grid(True)
        lines, labels = self.angle_ax.get_legend_handles_labels()
        lines2, labels2 = self.distance_ax.get_legend_handles_labels()
        self.distance_ax.legend(lines + lines2, labels + labels2, loc='upper left')
        self.angle_canvas.draw()

    def create_connection_group(self, port_type, baud_rate):
        group = QGroupBox(f"Kết nối {port_type} (Baud: {baud_rate})")
        layout = QGridLayout()
        combo = QComboBox()
        connect_button = QPushButton("Kết nối")
        disconnect_button = QPushButton("Ngắt kết nối")
        status_label = QLabel("Chưa kết nối")
        status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(QLabel("Cổng COM:"), 0, 0)
        layout.addWidget(combo, 0, 1)
        layout.addWidget(connect_button, 1, 0)
        layout.addWidget(disconnect_button, 1, 1)
        layout.addWidget(status_label, 0, 2, 2, 1, Qt.AlignCenter)
        group.setLayout(layout)
        if port_type == "MKS":
            self.mks_com_combo = combo
            self.mks_connect_button = connect_button
            self.mks_disconnect_button = disconnect_button
            self.mks_status_label = status_label
        else:
            self.arduino_com_combo = combo
            self.arduino_connect_button = connect_button
            self.arduino_disconnect_button = disconnect_button
            self.arduino_status_label = status_label
        return group

    def refresh_com_ports(self):
        self.mks_com_combo.clear()
        self.arduino_com_combo.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.mks_com_combo.addItem("Không có")
            self.arduino_com_combo.addItem("Không có")
        else:
            for port in ports:
                self.mks_com_combo.addItem(port.device)
                self.arduino_com_combo.addItem(port.device)

    def connect_port(self, port_type):
        if port_type == "MKS":
            port_name = self.mks_com_combo.currentText()
            baud_rate = 9600
        else:
            port_name = self.arduino_com_combo.currentText()
            baud_rate = 115200
        if (port_type == "MKS" and self.mks_port and self.mks_port.is_open) or (
                port_type == "Arduino" and self.arduino_port and self.arduino_port.is_open): return
        if not port_name or "Không có" in port_name:
            self.log_console.append(f"HỆ THỐNG: Lỗi - Vui lòng chọn cổng COM cho {port_type}.")
            return
        try:
            port_instance = serial.Serial(port_name, baud_rate, timeout=1)
            self.log_console.append(f"HỆ THỐNG: Đang kết nối {port_type} tới {port_name}...")
            reader_instance = SerialReader(port_instance, port_type)
            reader_instance.data_received.connect(self.process_incoming_data)
            reader_instance.start()
            if port_type == "MKS":
                self.mks_port = port_instance
                self.mks_reader = reader_instance
                self.mks_status_label.setText("Đã kết nối")
                self.mks_status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.arduino_port = port_instance
                self.arduino_reader = reader_instance
                self.arduino_status_label.setText("Đã kết nối")
                self.arduino_status_label.setStyleSheet("color: green; font-weight: bold;")
        except serial.SerialException as e:
            self.log_console.append(f"HỆ THỐNG: Lỗi kết nối {port_type} - {e}")

    def disconnect_port(self, port_type):
        if port_type == "MKS":
            if self.mks_reader: self.mks_reader.stop(); self.mks_reader.wait()
            if self.mks_port and self.mks_port.is_open: self.mks_port.close()
            self.mks_status_label.setText("Chưa kết nối")
            self.mks_status_label.setStyleSheet("color: black;")
        else:
            if self.arduino_reader: self.arduino_reader.stop(); self.arduino_reader.wait()
            if self.arduino_port and self.arduino_port.is_open: self.arduino_port.close()
            self.arduino_status_label.setText("Chưa kết nối")
            self.arduino_status_label.setStyleSheet("color: black;")
        self.log_console.append(f"HỆ THỐNG: Đã ngắt kết nối {port_type}.")

    def send_command(self, port_type, cmd):
        port_to_use = self.mks_port if port_type == "MKS" else self.arduino_port
        if port_to_use and port_to_use.is_open:
            port_to_use.write((cmd + '\n').encode('utf-8'))
            self.log_console.append(f"GUI > {port_type} > {cmd}")
        else:
            self.log_console.append(f"HỆ THỐNG: Lỗi - Chưa kết nối cổng {port_type}.")

    def send_move_command(self, action):
        self.send_command("MKS", f"{action}:{self.main_drive_steps_input.text()}:{self.main_drive_speed_input.text()}")

    def send_clamp_command(self):
        self.send_command("MKS", f"r:{self.clamp_steps_input.text()}:{self.clamp_speed_input.text()}")

    def send_release_command(self):
        self.send_command("MKS", f"l:{self.clamp_steps_input.text()}:{self.clamp_speed_input.text()}")

    def closeEvent(self, event):
        if self.is_recording:
            self.stop_recording()
        self.disconnect_port("MKS")
        self.disconnect_port("Arduino")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())