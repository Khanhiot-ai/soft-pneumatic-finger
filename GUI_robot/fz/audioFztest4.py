import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import PyDAQmx
from PyDAQmx import Task
import threading


# ================= ATINano17Reader =================
class ATINano17Reader:
    def __init__(self, device_name, channels, sample_rate, num_samples, calibration_matrix):
        self.device_name = device_name
        self.channels = channels
        self.sample_rate = sample_rate
        self.num_samples = num_samples
        self.calibration_matrix = calibration_matrix
        self.task = Task()
        self.data = np.zeros((len(self.channels), self.num_samples))
        self.fz_data = np.array([])
        self.timestamps = np.array([])
        self.fz_offset = 0
        self.update_interval = 10   # ms
        self.num_data_display = 1000
        self.lock = threading.Lock()
        self.running = False

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
        self.configure_task()
        self.task.StartTask()
        self.running = True

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
        self.task.StopTask()
        self.task.ClearTask()
        self.running = False

    def run_reader(self):
        self.start()
        count = 0
        while self.running:
            self.read_data()
            forces = self.convert_to_force()
            fz = forces[2][0] - self.fz_offset
            timestamp = count * self.update_interval / 1000.0

            with self.lock:
                self.fz_data = np.append(self.fz_data, fz)
                self.timestamps = np.append(self.timestamps, timestamp)

                if self.fz_data.size == 10:
                    self.fz_offset = np.mean(self.fz_data)

                if self.fz_data.size > self.num_data_display:
                    self.fz_data = self.fz_data[1:]
                    self.timestamps = self.timestamps[1:]

            count += 1

    def reset_offset(self):
        with self.lock:
            if self.fz_data.size >= 200:
                self.fz_offset += np.mean(self.fz_data[-200:])
                print("Fz offset recalculated")

    def get_data(self):
        with self.lock:
            return self.fz_data, self.timestamps


# ================= SensorUI =================
class SensorUI(QtWidgets.QMainWindow):
    def __init__(self, force_reader):
        super().__init__()
        self.force_reader = force_reader
        self.init_ui()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.force_running = False

    def init_ui(self):
        self.setWindowTitle("ATI Nano17 Force Z GUI")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)

        # Force Sensor Plot
        self.plot_widget = pg.GraphicsLayoutWidget()
        self.plot_widget.setBackground('w')
        self.force_plot = self.plot_widget.addPlot(title="Force Z Data")
        self.force_plot.setLabel('left', 'Force (N)')
        self.force_plot.setLabel('bottom', 'Sample')
        self.fz_curve = self.force_plot.plot(pen=pg.mkPen('b', width=2))
        self.force_plot.setYRange(-5, 5)
        layout.addWidget(self.plot_widget)

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

        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.clicked.connect(self.close_app)
        button_layout.addWidget(self.close_button)

        layout.addWidget(button_panel)

    def start_force(self):
        self.force_reader_thread = threading.Thread(target=self.force_reader.run_reader)
        self.force_reader_thread.start()
        self.force_running = True
        if not self.timer.isActive():
            self.timer.start(self.force_reader.update_interval)

    def stop_force(self):
        self.force_reader.stop()
        self.force_reader_thread.join()
        self.force_running = False
        self.timer.stop()

    def close_app(self):
        self.stop_force()
        QtWidgets.QApplication.quit()

    def update_plots(self):
        fz_data, _ = self.force_reader.get_data()
        self.fz_curve.setData(fz_data)
        QtWidgets.QApplication.processEvents()


# ================= Main =================
def main():
    device_name = "Dev1"
    channels = ["ai0", "ai1", "ai2", "ai3", "ai4", "ai5"]
    sample_rate = 1000.0
    num_samples = 1
    calibration_matrix = np.array([
        [-0.01204,  0.04072, -0.00491, -3.17693, -0.09011,  3.20056],
        [ 0.04877,  4.16255, -0.02547, -1.81391,  0.10208, -1.88871],
        [ 3.76907, -0.08275,  3.80119,  0.08022,  3.79020,  0.15491],
        [ 0.09941, 25.58867, 21.46188, -10.72741, -20.55362, -12.46830],
        [-23.96291,  0.38248, 12.34451, 19.63954, 12.85597, -19.10214],
        [ 0.48486, 17.25499, -0.09982, 15.21282, -0.55950, 15.49801]
    ])

    app = QtWidgets.QApplication(sys.argv)
    force_reader = ATINano17Reader(device_name, channels, sample_rate, num_samples, calibration_matrix)
    ui = SensorUI(force_reader)
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
