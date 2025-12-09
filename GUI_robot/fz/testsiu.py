################## ONLY PLOT Z###########################

import sys
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QHBoxLayout
from PyQt5.QtCore import pyqtSignal, QThread
import pyqtgraph as pg
import keyboard
from filterClass import lowPass  # Import lowPass filter class

# Define the 6x6 matrix (force and torque matrix of nano17)
matrix = np.array([
    [-0.01204,  0.04072, -0.00491, -3.17693, -0.09011,  3.20056],
    [ 0.04877,  4.16255, -0.02547, -1.81391,  0.10208, -1.88871],
    [ 3.76907, -0.08275,  3.80119,  0.08022,  3.79020,  0.15491],
    [ 0.09941, 25.58867, 21.46188, -10.72741, -20.55362, -12.46830],
    [-23.96291,  0.38248, 12.34451, 19.63954, 12.85597, -19.10214],
    [ 0.48486, 17.25499, -0.09982, 15.21282, -0.55950, 15.49801]
])

class DataGenerator(QThread):
    new_data = pyqtSignal(float)

    def __init__(self, samples_per_channel, sample_rate):
        super().__init__()
        self.samples_per_channel = samples_per_channel
        self.sample_rate = sample_rate
        self.running = False
        self.offset_samples_limit = 200  # Number of samples to collect for offset calculation
        self.offset_data = []  # List to store the first 200 rows for offset calculation
        self.filter = lowPass(2, 0.005, 10)  # Low-pass filter for the third column
        self.window_size = 10  # Window size for moving average filter
        self.ma_data_buffer = np.zeros(self.window_size)  # Buffer to store recent data for moving average

    def moving_average_filter(self, data):
        self.ma_data_buffer = np.roll(self.ma_data_buffer, -1)
        self.ma_data_buffer[-1] = data
        return np.mean(self.ma_data_buffer) # Return the average of the buffer

    def run(self):
        self.running = True
        with nidaqmx.Task() as task:
            for i in range(6):
                task.ai_channels.add_ai_voltage_chan(f"Dev1/ai{i}", min_val=0.0, max_val=5.0)

            task.timing.cfg_samp_clk_timing(rate=self.sample_rate, sample_mode=AcquisitionType.CONTINUOUS)
            task.start()

            while self.running:
                data = task.read(number_of_samples_per_channel=self.samples_per_channel)
                data_np = matrix @ data
                new_data = -np.array(data_np).T

                # Collect the first 200 rows for offset calculation
                if len(self.offset_data) < self.offset_samples_limit:
                    self.offset_data.append(new_data[0, :6])
                    continue

                # Use the collected data to compute the offset
                offset = np.mean(self.offset_data, axis=0)  # Calculate the average offset

                new_data -= offset
                third_col = new_data[:, 2]
                filtered_data = np.array([self.filter.Work(sample) for sample in third_col])
                ma_filtered_data = np.array([self.moving_average_filter(sample) for sample in filtered_data])

                self.new_data.emit(ma_filtered_data[-1])

                if keyboard.is_pressed('space'):
                    print("Spacebar pressed. Stopping data acquisition.")
                    self.running = False
                    break

    def stop(self):
        self.running = False
        self.wait()

class LivePlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Live Data Plot')
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)

        self.plot_widget.setBackground('w')
        self.plot_widget.addLegend()

        self.samples_per_channel = 200
        self.sample_rate = 40000
        self.buffer_size = 1000  # Set buffer size to 1000 points

        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2), name='Channel Z')
        self.data_buffer = np.zeros(self.buffer_size)

        self.plot_widget.setXRange(0, self.buffer_size)
        self.plot_widget.setYRange(-2, 2)
        self.plot_widget.setLimits(xMin=0, xMax=1000, yMin=-2, yMax=2)

        self.force_label = QLabel('Force Z: 0.0')
        force_layout = QHBoxLayout()
        force_layout.addWidget(self.force_label)
        self.layout.addLayout(force_layout)

        self.data_generator = DataGenerator(self.samples_per_channel, self.sample_rate)
        self.data_generator.new_data.connect(self.update_plot)
        self.data_generator.start()

    def update_plot(self, data):
        self.data_buffer = np.roll(self.data_buffer, -1)
        self.data_buffer[-1] = data
        self.curve.setData(self.data_buffer)
        self.force_label.setText(f'Force Z: {data:.2f}')

    def closeEvent(self, event):
        self.data_generator.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LivePlotWindow()
    window.show()
    sys.exit(app.exec_())
