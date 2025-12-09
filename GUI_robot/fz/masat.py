import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import PyDAQmx
from PyDAQmx import Task
import threading
import csv
import datetime
import time ### THAY ĐỔI ###: Thêm thư viện time


# ================= ATINano17Reader =================
class ATINano17Reader:
    def __init__(self, device_name, channels, sample_rate, num_samples, calibration_matrix):
        self.device_name = device_name
        self.channels = channels
        self.sample_rate = sample_rate
        self.num_samples = num_samples
        self.calibration_matrix = calibration_matrix
        self.task = None
        self.data = np.zeros((len(self.channels), self.num_samples))

        # dữ liệu Fx, Fy, Fz
        self.fx_data = np.array([])
        self.fy_data = np.array([])
        self.fz_data = np.array([])
        self.timestamps = np.array([])

        self.fx_offset = 0
        self.fy_offset = 0
        self.fz_offset = 0

        self.update_interval = 100  # ms (0.1 giây)
        self.num_data_display = 1000
        self.lock = threading.Lock()
        self.running = False

        # logging
        self.logging = False
        self.csv_file = None
        self.csv_writer = None
        
        ### THAY ĐỔI ###: Thêm các biến để kiểm soát tốc độ ghi file
        # Bạn có thể thay đổi giá trị này. 0.2 nghĩa là ghi 5 lần mỗi giây.
        self.log_interval = 0.1  # (giây)
        self.last_log_time = 0

    def configure_task(self):
        channel_str = ",".join([f"{self.device_name}/{ch}" for ch in self.channels])
        self.task.CreateAIVoltageChan(
            channel_str, "",
            PyDAQmx.DAQmx_Val_Cfg_Default,
            -10.0, 10.0,
            PyDAQmx.DAQmx_Val_Volts, None
        )
        self.task.CfgSampClkTiming(
            "",
            self.sample_rate,
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps,
            self.num_samples
        )

    def start(self):
        try:
            if self.task:
                self.task.StopTask()
                self.task.ClearTask()
        except:
            pass

        self.task = Task()
        self.configure_task()
        self.task.StartTask()
        self.running = True
        print("DAQ Task started")

    def read_data(self):
        read = PyDAQmx.int32()
        data = np.zeros((len(self.channels) * self.num_samples,), dtype=np.float64)
        self.task.ReadAnalogF64(
            self.num_samples,
            10.0,
            PyDAQmx.DAQmx_Val_GroupByChannel,
            data, len(data),
            PyDAQmx.byref(read), None
        )
        self.data = data.reshape((len(self.channels), self.num_samples))

    def convert_to_force(self):
        return np.dot(self.calibration_matrix, self.data)

    def stop(self):
        try:
            if self.task:
                self.task.StopTask()
                self.task.ClearTask()
                print("DAQ Task stopped and cleared")
        except Exception as e:
            print("Warning when stopping task:", e)
        finally:
            self.task = None
            self.running = False
            self.stop_logging()

    def run_reader(self):
        count = 0
        while self.running:
            self.read_data()
            forces = self.convert_to_force()

            fx = forces[0][0] - self.fx_offset
            fy = forces[1][0] - self.fy_offset
            fz = forces[2][0] - self.fz_offset
            timestamp = count * self.update_interval / 1000.0

            with self.lock:
                self.fx_data = np.append(self.fx_data, fx)
                self.fy_data = np.append(self.fy_data, fy)
                self.fz_data = np.append(self.fz_data, fz)
                self.timestamps = np.append(self.timestamps, timestamp)

                if self.fx_data.size == 10:
                    self.fx_offset = np.mean(self.fx_data)
                    self.fy_offset = np.mean(self.fy_data)
                    self.fz_offset = np.mean(self.fz_data)

                if self.fx_data.size > self.num_data_display:
                    self.fx_data = self.fx_data[1:]
                    self.fy_data = self.fy_data[1:]
                    self.fz_data = self.fz_data[1:]
                    self.timestamps = self.timestamps[1:]

                ### THAY ĐỔI ###: Logic ghi file được kiểm soát bằng thời gian
                current_time = time.time()
                if self.logging and self.csv_writer and (current_time - self.last_log_time >= self.log_interval):
                    self.csv_writer.writerow([timestamp, fx, fy, fz])
                    self.last_log_time = current_time  # Cập nhật lại thời gian đã ghi

            count += 1

    def reset_offset(self):
        with self.lock:
            if self.fz_data.size >= 200:
                self.fx_offset += np.mean(self.fx_data[-200:])
                self.fy_offset += np.mean(self.fy_data[-200:])
                self.fz_offset += np.mean(self.fz_data[-200:])
                print("Offsets recalculated (Fx, Fy, Fz)")

    def get_data(self):
        with self.lock:
            return self.fx_data, self.fy_data, self.fz_data, self.timestamps

    def start_logging(self):
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"force_data_{timestamp_str}.csv"

        if self.logging:
            self.stop_logging()

        self.csv_file = open(filename, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["Time (s)", "Fx (N)", "Fy (N)", "Fz (N)"])
        self.logging = True
        
        ### THAY ĐỔI ###: Đặt lại thời gian bắt đầu ghi để đảm bảo ghi ngay lập tức
        self.last_log_time = time.time()
        print(f"Logging started -> {filename}")

    def stop_logging(self):
        if self.logging and self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.logging = False
            print("Logging stopped, file saved.")


# ================= SensorUI (Không thay đổi) =================
class SensorUI(QtWidgets.QMainWindow):
    def __init__(self, force_reader):
        super().__init__()
        self.force_reader = force_reader
        self.init_ui()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.force_running = False

    def init_ui(self):
        self.setWindowTitle("ATI Nano17 Force GUI (Fx, Fy, Fz)")
        self.setGeometry(100, 100, 800, 800)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)

        # Plot Fx
        self.plot_widget_fx = pg.GraphicsLayoutWidget()
        self.plot_widget_fx.setBackground('w')
        self.fx_plot = self.plot_widget_fx.addPlot(title="Force X Data")
        self.fx_plot.setLabel('left', 'Force (N)')
        self.fx_plot.setLabel('bottom', 'Sample')
        self.fx_curve = self.fx_plot.plot(pen=pg.mkPen('r', width=2))
        self.fx_plot.setYRange(-5, 5)
        layout.addWidget(self.plot_widget_fx)

        # Plot Fy
        self.plot_widget_fy = pg.GraphicsLayoutWidget()
        self.plot_widget_fy.setBackground('w')
        self.fy_plot = self.plot_widget_fy.addPlot(title="Force Y Data")
        self.fy_plot.setLabel('left', 'Force (N)')
        self.fy_plot.setLabel('bottom', 'Sample')
        self.fy_curve = self.fy_plot.plot(pen=pg.mkPen('g', width=2))
        self.fy_plot.setYRange(-5, 5)
        layout.addWidget(self.plot_widget_fy)

        # Plot Fz
        self.plot_widget_fz = pg.GraphicsLayoutWidget()
        self.plot_widget_fz.setBackground('w')
        self.fz_plot = self.plot_widget_fz.addPlot(title="Force Z Data")
        self.fz_plot.setLabel('left', 'Force (N)')
        self.fz_plot.setLabel('bottom', 'Sample')
        self.fz_curve = self.fz_plot.plot(pen=pg.mkPen('b', width=2))
        self.fz_plot.setYRange(-5, 5)
        layout.addWidget(self.plot_widget_fz)

        # Buttons
        button_panel = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout()
        button_panel.setLayout(button_layout)

        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.clicked.connect(self.start_force)
        button_layout.addWidget(self.start_button)

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_force)
        button_layout.addWidget(self.stop_button)

        self.reset_button = QtWidgets.QPushButton("Reset Offset")
        self.reset_button.clicked.connect(self.force_reader.reset_offset)
        button_layout.addWidget(self.reset_button)

        self.log_start_button = QtWidgets.QPushButton("Start Logging")
        self.log_start_button.clicked.connect(self.force_reader.start_logging)
        button_layout.addWidget(self.log_start_button)

        self.log_stop_button = QtWidgets.QPushButton("Stop Logging")
        self.log_stop_button.clicked.connect(self.force_reader.stop_logging)
        button_layout.addWidget(self.log_stop_button)

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.close_button)

        layout.addWidget(button_panel)

    def closeEvent(self, event):
        print("Window close event triggered. Shutting down cleanly.")
        self.close_app()
        event.accept()

    def start_force(self):
        if not self.force_running:
            self.force_reader.start()
            self.force_reader_thread = threading.Thread(target=self.force_reader.run_reader)
            self.force_reader_thread.start()
            self.force_running = True
            if not self.timer.isActive():
                self.timer.start(self.force_reader.update_interval)

    def stop_force(self):
        self.force_reader.stop()
        if hasattr(self, "force_reader_thread"):
            self.force_reader_thread.join()
        self.force_running = False
        self.timer.stop()

    def close_app(self):
        self.stop_force()
        QtWidgets.QApplication.quit()

    def update_plots(self):
        fx_data, fy_data, fz_data, _ = self.force_reader.get_data()
        self.fx_curve.setData(fx_data)
        self.fy_curve.setData(fy_data)
        self.fz_curve.setData(fz_data)
        QtWidgets.QApplication.processEvents()


# ================= Main (Không thay đổi) =================
def main():
    device_name = "Dev1"
    channels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
    sample_rate = 1000.0
    num_samples = 1
    calibration_matrix = np.array([
        [-0.01204, 0.04072, -0.00491, -3.17693, -0.09011, 3.20056],
        [0.04877, 4.16255, -0.02547, -1.81391, 0.10208, -1.88871],
        [3.76907, -0.08275, 3.80119, 0.08022, 3.79020, 0.15491],
        [0.09941, 25.58867, 21.46188, -10.72741, -20.55362, -12.46830],
        [-23.96291, 0.38248, 12.34451, 19.63954, 12.85597, -19.10214],
        [0.48486, 17.25499, -0.09982, 15.21282, -0.55950, 15.49801]
    ])

    app = QtWidgets.QApplication(sys.argv)
    force_reader = ATINano17Reader(device_name, channels, sample_rate, num_samples, calibration_matrix)
    ui = SensorUI(force_reader)
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()