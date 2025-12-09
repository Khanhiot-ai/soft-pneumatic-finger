import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QTextEdit,
                             QComboBox, QGridLayout, QGroupBox, QMessageBox)
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import QIODevice, QTimer


class StepperMotorGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_port = QSerialPort(self)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Bảng Điều Khiển Động Cơ Bước")
        self.setGeometry(100, 100, 650, 500)

        main_layout = QVBoxLayout(self)

        # Khu vực kết nối
        connection_group = QGroupBox("Kết nối")
        main_layout.addWidget(connection_group)
        connection_layout = QHBoxLayout(connection_group)
        self.port_combo = QComboBox()
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_connect = QPushButton("Kết nối")
        self.status_label = QLabel("Chưa kết nối")
        connection_layout.addWidget(QLabel("Cổng COM:"))
        connection_layout.addWidget(self.port_combo)
        connection_layout.addWidget(self.btn_refresh)
        connection_layout.addWidget(self.btn_connect)
        connection_layout.addStretch()
        connection_layout.addWidget(self.status_label)

        # Khu vực điều khiển
        control_grid = QGridLayout()
        main_layout.addLayout(control_grid)

        # Điều khiển Lên/Xuống
        updown_group = QGroupBox("Lên/Xuống (E0, E1)")
        control_grid.addWidget(updown_group, 0, 0)
        updown_layout = QGridLayout(updown_group)
        self.steps_updown_input = QLineEdit("2000")
        self.speed_updown_input = QLineEdit("1600")
        self.btn_up = QPushButton("Đi Lên (u)")
        self.btn_down = QPushButton("Đi Xuống (d)")
        updown_layout.addWidget(QLabel("Số bước:"), 0, 0)
        updown_layout.addWidget(self.steps_updown_input, 0, 1)
        updown_layout.addWidget(QLabel("Tốc độ:"), 1, 0)
        updown_layout.addWidget(self.speed_updown_input, 1, 1)
        updown_layout.addWidget(self.btn_up, 2, 0)
        updown_layout.addWidget(self.btn_down, 2, 1)

        # Điều khiển Kẹp/Nhả
        clamp_group = QGroupBox("Kẹp/Nhả (X)")
        control_grid.addWidget(clamp_group, 0, 1)
        clamp_layout = QGridLayout(clamp_group)
        self.steps_clamp_input = QLineEdit("400")
        self.speed_clamp_input = QLineEdit("1000")
        self.btn_clamp = QPushButton("Kẹp (c)")
        self.btn_release = QPushButton("Nhả (r)")
        clamp_layout.addWidget(QLabel("Số bước:"), 0, 0)
        clamp_layout.addWidget(self.steps_clamp_input, 0, 1)
        clamp_layout.addWidget(QLabel("Tốc độ:"), 1, 0)
        clamp_layout.addWidget(self.speed_clamp_input, 1, 1)
        clamp_layout.addWidget(self.btn_clamp, 2, 0)
        clamp_layout.addWidget(self.btn_release, 2, 1)

        # Điều khiển chung
        general_group = QGroupBox("Chung")
        main_layout.addWidget(general_group)
        general_layout = QHBoxLayout(general_group)
        self.btn_enable = QPushButton("Kích hoạt (e)")
        self.btn_disable = QPushButton("Vô hiệu hóa (x)")
        self.btn_stop = QPushButton("DỪNG (stop)")
        self.btn_stop.setStyleSheet("background-color: #d9534f; color: white;")
        general_layout.addWidget(self.btn_enable)
        general_layout.addWidget(self.btn_disable)
        general_layout.addWidget(self.btn_stop)

        # Log
        log_group = QGroupBox("Log từ Arduino")
        main_layout.addWidget(log_group)
        log_layout = QVBoxLayout(log_group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)

        # Kết nối tín hiệu
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect.clicked.connect(self.toggle_connection)
        self.serial_port.readyRead.connect(self.receive_serial_data)

        self.btn_up.clicked.connect(
            lambda: self.send_move_command("u", self.steps_updown_input, self.speed_updown_input))
        self.btn_down.clicked.connect(
            lambda: self.send_move_command("d", self.steps_updown_input, self.speed_updown_input))
        self.btn_clamp.clicked.connect(
            lambda: self.send_move_command("c", self.steps_clamp_input, self.speed_clamp_input))
        self.btn_release.clicked.connect(
            lambda: self.send_move_command("r", self.steps_clamp_input, self.speed_clamp_input))

        self.btn_enable.clicked.connect(lambda: self.send_simple_command("e"))
        self.btn_disable.clicked.connect(lambda: self.send_simple_command("x"))
        self.btn_stop.clicked.connect(lambda: self.send_simple_command("stop"))

        self.refresh_ports()

    def refresh_ports(self):
        self.port_combo.clear()
        for port in QSerialPortInfo.availablePorts():
            self.port_combo.addItem(port.portName(), port)

    def toggle_connection(self):
        if self.serial_port.isOpen():
            self.serial_port.close()
            self.status_label.setText("Chưa kết nối")
            self.btn_connect.setText("Kết nối")
            self.log_output.clear()
        else:
            port = self.port_combo.currentData()
            if not port:
                QMessageBox.warning(self, "Lỗi", "Không có cổng COM nào được chọn.")
                return
            self.serial_port.setPort(port)
            self.serial_port.setBaudRate(QSerialPort.Baud9600)
            if self.serial_port.open(QIODevice.ReadWrite):
                self.status_label.setText(f"Đang kết nối...")
                self.btn_connect.setText("Ngắt kết nối")
                # ==========================================================
                # LOGIC HANDSHAKE MỚI: Gửi tín hiệu '1' để yêu cầu INIT
                # ==========================================================
                self.serial_port.write(b'1')
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể mở cổng {port.portName()}.")

    def receive_serial_data(self):
        while self.serial_port.canReadLine():
            try:
                line = self.serial_port.readLine().data().decode('utf-8', 'ignore').strip()
                if line:
                    self.log_output.append(f"ARDUINO: {line}")
                    # Thay đổi trạng thái khi nhận được tín hiệu INIT
                    if "INIT:" in line:
                        self.status_label.setText(f"Đã kết nối")
            except Exception as e:
                self.log_output.append(f"Lỗi đọc serial: {e}")

    def send_command(self, command_str):
        if not self.serial_port.isOpen():
            QMessageBox.warning(self, "Lỗi", "Chưa kết nối với Arduino.")
            return
        self.serial_port.write((command_str + "\n").encode('utf-8'))
        self.log_output.append(f"GUI SENT: {command_str}")

    def send_move_command(self, action, steps_widget, speed_widget):
        try:
            steps = int(steps_widget.text())
            speed = speed_widget.text().strip()
            command = f"{action}:{steps}"
            if speed and float(speed) > 0:
                command += f":{float(speed)}"
            self.send_command(command)
        except ValueError:
            QMessageBox.warning(self, "Lỗi", "Số bước và tốc độ phải là số hợp lệ.")

    def send_simple_command(self, action):
        self.send_command(action)

    def closeEvent(self, event):
        if self.serial_port.isOpen():
            self.serial_port.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = StepperMotorGUI()
    gui.show()
    sys.exit(app.exec_())