import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
import numpy as np
import pyaudio
import PyDAQmx
from PyDAQmx import Task
import sys
import filterClass
import time

CHUNK = 200
FORMAT = pyaudio.paFloat32
CHANNEL = 1
RATE = 48000
RECORD_SECONDS = 5000
GROUP_NUM = 4
CALC_NUM = 14
LOOP_COUNT = int(RECORD_SECONDS / 0.004)
T = float(CHUNK) / RATE / GROUP_NUM

dataRange = 1000
stop_flag = False  
close_flag = 0  

sin_wave_1 = np.zeros(CALC_NUM)
Amp_group_1 = np.arange(0, dataRange)
sum_temp_1 = 0
amp_ave_1 = 0
Amp_diff_1 = 0.0

sin_wave_2 = np.zeros(CALC_NUM)
Amp_group_2 = np.arange(0, dataRange)
sum_temp_2 = 0
amp_ave_2 = 0
Amp_diff_2 = 0.0

reset_cnt_1 = 0
runtime_1 = 0
reset_cnt_2 = 0
runtime_2 = 0

device_id_1 = 1
device_id_2 = 1

ft_lock = threading.Lock()

file_1 = open("stream1_data.txt", "w")
file_1.write("Time(s), Amplitude\n")

file_2 = open("stream2_data.txt", "w")
file_2.write("Time(s), Amplitude\n")

file_fz = open("fz_data.txt", "w")
file_fz.write("Time(s), Force_Z\n")

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
        self.data_to_save = []
        self.fz_offset = 0
        self.update_interval = 1
        self.num_data_display = 1000
        self.lock = threading.Lock()
        self.running = False

    def configure_task(self):
        channel_str = ",".join([f"{self.device_name}/{channel}" for channel in self.channels])
        self.task.CreateAIVoltageChan(
            channel_str,
            "",
            PyDAQmx.DAQmx_Val_Cfg_Default,
            -10.0,
            10.0,
            PyDAQmx.DAQmx_Val_Volts,
            None
        )
        self.task.CfgSampClkTiming(
            "",
            self.sample_rate,
            PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps,
            self.num_samples
        )
        self.task.CfgInputBuffer(1000)

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
            data,
            len(data),
            PyDAQmx.byref(read),
            None
        )
        self.data = data.reshape((len(self.channels), self.num_samples))

    def convert_to_force(self):
        forces = np.dot(self.calibration_matrix, self.data)
        return forces

    def stop(self):
        self.task.StopTask()
        self.task.ClearTask()
        self.running = False

    def run_reader(self):
        self.start()
        timestamp = 0
        count = 0
        while self.running:
            self.read_data()
            forces = self.convert_to_force()
            fz = forces[2][0] - self.fz_offset
            timestamp = count * self.update_interval / 1000.0

            with self.lock:
                self.fz_data = np.append(self.fz_data, fz)
                self.timestamps = np.append(self.timestamps, timestamp)
                self.data_to_save.append((timestamp, fz))

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

    
p = pyaudio.PyAudio()
stream1 = p.open(format=FORMAT, channels=CHANNEL, rate=RATE, input=True, input_device_index=device_id_1, frames_per_buffer=CHUNK)
stream2 = p.open(format=FORMAT, channels=CHANNEL, rate=RATE, input=True, input_device_index=device_id_2, frames_per_buffer=CHUNK)


def audio_process_1():
    print("* recording stream 1")
    global sin_wave_1, Amp_group_1, sum_temp_1, reset_cnt_1, amp_ave_1, runtime_1, Amp_diff_1, stop_flag 
    for i in range(0, LOOP_COUNT):
        if stop_flag:  
            break
        rw_data_1 = stream1.read(CHUNK, exception_on_overflow=False)
        rw_data_1 = np.frombuffer(rw_data_1, dtype=np.float32)

        for j in range(0, GROUP_NUM):
            for k in range(0, CALC_NUM):
                sin_wave_1[k] = rw_data_1[int(CHUNK / GROUP_NUM) * j + k]
            Amp_temp_1 = max(sin_wave_1) - min(sin_wave_1)
            Amp_diff_1 = filterL1.Work(Amp_temp_1 - amp_ave_1) 
            Amp_group_1 = np.append(Amp_group_1, Amp_diff_1)
            Amp_group_1 = np.delete(Amp_group_1, 0)

            # Ghi vào file
            file_1.write(f"{runtime_1:.4f}, {Amp_diff_1:.8f}\n")


        if reset_cnt_1 < 200:
            reset_cnt_1 += 1
            sum_temp_1 += Amp_temp_1
        if reset_cnt_1 == 200:
            amp_ave_1 = sum_temp_1 / 200

        runtime_1 = round((i * T * GROUP_NUM), 1)
    print("* done recording stream 1")

def audio_process_2():
    print("* recording stream 2")
    global sin_wave_2, Amp_group_2, sum_temp_2, reset_cnt_2, amp_ave_2, runtime_2, Amp_diff_2, stop_flag
    for i in range(0, LOOP_COUNT):
        if stop_flag:  
            break
        rw_data_2 = stream2.read(CHUNK, exception_on_overflow=False)
        rw_data_2 = np.frombuffer(rw_data_2, dtype=np.float32)

        for j in range(0, GROUP_NUM):
            for k in range(0, CALC_NUM):
                sin_wave_2[k] = rw_data_2[int(CHUNK / GROUP_NUM) * j + k]
            Amp_temp_2 = max(sin_wave_2) - min(sin_wave_2)
            Amp_diff_2 = filterL2.Work(Amp_temp_2 - amp_ave_2)  
            Amp_group_2 = np.append(Amp_group_2, Amp_diff_2)
            Amp_group_2 = np.delete(Amp_group_2, 0)

            # Ghi vào file
            file_2.write(f"{runtime_2:.4f}, {Amp_diff_2:.8f}\n")


        if reset_cnt_2 < 200:
            reset_cnt_2 += 1
            sum_temp_2 += Amp_temp_2
        if reset_cnt_2 == 200:
            amp_ave_2 = sum_temp_2 / 200

        runtime_2 = round((i * T * GROUP_NUM), 1)
    print("* done recording stream 2")


FT_channel = "Dev1/ai0:5" 
FT_matrix = np.array([
    [-0.01204,  0.04072, -0.00491, -3.17693, -0.09011,  3.20056],
    [ 0.04877,  4.16255, -0.02547, -1.81391,  0.10208, -1.88871],
    [ 3.76907, -0.08275,  3.80119,  0.08022,  3.79020,  0.15491],
    [ 0.09941, 25.58867, 21.46188, -10.72741, -20.55362, -12.46830],
    [-23.96291,  0.38248, 12.34451, 19.63954, 12.85597, -19.10214],
    [ 0.48486, 17.25499, -0.09982, 15.21282, -0.55950, 15.49801]
])

FT_bias = np.zeros(6) 
FT_data = np.zeros((6, 1000))  


class DAQThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.task = Task()
        self.task.CreateAIVoltageChan(
            FT_channel, "", PyDAQmx.DAQmx_Val_Cfg_Default,
            -10.0, 10.0, PyDAQmx.DAQmx_Val_Volts, None
        )
        self.task.CfgSampClkTiming(
            "", 1000.0, PyDAQmx.DAQmx_Val_Rising,
            PyDAQmx.DAQmx_Val_ContSamps, 100
        )
        self.task.StartTask()
        self.running = True
        self.start_time = None
        self.fz_offset = 0  

        # 🔹 calibrate ngay khi khởi động
        self.calibrate_fz_offset()

    def calibrate_fz_offset(self, num_samples=200):
        """Hiệu chuẩn Fz offset khi không có lực tác động"""
        offset_values = []
        raw = np.zeros(6)
        for _ in range(num_samples):
            self.task.ReadAnalogF64(
                1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,
                raw, 6, None, None
            )
            force = np.dot(FT_matrix, raw - FT_bias)
            offset_values.append(force[2])
            time.sleep(0.002)
        self.fz_offset = np.mean(offset_values)
        print(f"[DAQ] Fz offset calibrated: {self.fz_offset:.3f} N")

    def run(self):
        global FT_data
        raw = np.zeros(6)
        self.start_time = time.time()

        while self.running:
            try:
                self.task.ReadAnalogF64(
                    1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,
                    raw, 6, None, None
                )
                force = np.dot(FT_matrix, raw - FT_bias)
                fz_value = force[2] - self.fz_offset
            except Exception:
                force = np.zeros(6)
                fz_value = 0.0

            self.runtime_fz = time.time() - self.start_time
            file_fz.write(f"{self.runtime_fz:.4f}, {fz_value:.8f}\n")

            with ft_lock:
                FT_data = np.roll(FT_data, -1, axis=1)
                FT_data[:, -1] = force
                FT_data[2, -1] = fz_value


    def reset_offset(self):
        """Cho phép recalib lại offset khi đang chạy"""
        self.calibrate_fz_offset()

    def stop(self):
        self.running = False
        self.task.StopTask()
        self.task.ClearTask()

app = QApplication(sys.argv)
win = QMainWindow()
area = DockArea()
win.setCentralWidget(area)
win.resize(1200, 600)
win.setWindowTitle("TACTILE FEEDBACK")

d1 = Dock("Audio_Gen", size=(1, 1))
d3 = Dock("Audio_process", size=(5, 5))
area.addDock(d1, 'left')
area.addDock(d3, 'right')


def setup_plots():
    global w3_1, w3_2, curve_1, curve_2
    global w4_1, w4_2, raw_curve_1, raw_curve_2
    global w_corr, curve_corr

    w3_1 = pg.PlotWidget(title="Changed Amp - Device 1 ")
    curve_1 = w3_1.plot(pen=pg.mkPen('y', width=1))
    w3_1.setXRange(0, dataRange, padding=0.005)
    w3_1.setYRange(-0.1, 0.1, padding=0.005)
    d3.addWidget(w3_1, row=1, col=0)

    w3_2 = pg.PlotWidget(title="Changed Amp - Device 2 ")
    curve_2 = w3_2.plot(pen=pg.mkPen('c', width=1))
    w3_2.setXRange(0, dataRange, padding=0.005)
    w3_2.setYRange(-0.1, 0.1, padding=0.005)
    d3.addWidget(w3_2, row=1, col=1)

    w4_1 = pg.PlotWidget(title="Raw Amp - Device 1 ")
    raw_curve_1 = w4_1.plot(pen=pg.mkPen('r', width=1))
    w4_1.setXRange(0, CALC_NUM - 1, padding=0.005)
    w4_1.setYRange(-1.0, 1.0, padding=0.005)
    d3.addWidget(w4_1, row=2, col=0)

    w4_2 = pg.PlotWidget(title="Raw Amp - Device 2 ")
    raw_curve_2 = w4_2.plot(pen=pg.mkPen('g', width=1))
    w4_2.setXRange(0, CALC_NUM - 1, padding=0.005)
    w4_2.setYRange(-1.0, 1.0, padding=0.005)
    d3.addWidget(w4_2, row=2, col=1)
    
    
    w_corr = pg.PlotWidget(title="Correlation: Amp_group2 vs Amp_group1")

    curve_corr = w_corr.plot(pen=pg.mkPen('b', width=1), connect='all') 
    w_corr.setXRange(-0.5, 0.5, padding=0.01)
    w_corr.setYRange(-0.5, 0.5, padding=0.01)
    w_corr.setLabel('bottom', 'Amp_group_2')
    w_corr.setLabel('left', 'Amp_group_1')
    d3.addWidget(w_corr, row=1, col=2, rowspan=2)

def setup_force_plots():
    global force_plot_fz, curve_fz

    force_plot_fz = pg.PlotWidget(title="Force - Fz")
    curve_fz = force_plot_fz.plot(pen=pg.mkPen('m', width=2))
    force_plot_fz.setYRange(-10, 10)
    runtime_fz = pg.TextItem(text="Runtime: 0.00 s", color='w', anchor=(1, 1))
    force_plot_fz.addItem(runtime_fz)
    runtime_fz.setPos(0, 10)  # Đặt ở góc trái trên

    d3.addWidget(force_plot_fz, row=3, col=0, colspan=3)

def run_program():
    if (sys.flags.interactive != 1) or not hasattr(QApplication, 'instance'):
        QApplication.instance().exec_()

def update():
    global daq_thread
    w3_1.setTitle('Run Time: %0.1f s (Device 1)' % runtime_1)
    w3_2.setTitle('Run Time: %0.1f s (Device 2)' % runtime_2)
    runtime_fz = daq_thread.runtime_fz if daq_thread is not None else 0
    force_plot_fz.setTitle('Run Time: %0.1f s (Force Sensor)' % runtime_fz)
    
    curve_1.setData(Amp_group_1)
    curve_2.setData(Amp_group_2)
    raw_curve_1.setData(sin_wave_1)
    raw_curve_2.setData(sin_wave_2)
    
    curve_fz.setData(FT_data[2])
    
    length = min(len(Amp_group_1), len(Amp_group_2), 200)
    amp1 = Amp_group_1[-length:]
    amp2 = Amp_group_2[-length:]
    curve_corr.setData(amp2, amp1)

    app.processEvents()

def run_thread():
    global close_flag, th1, th2
    if close_flag != 1:
        th1.start()
        th2.start()

def reset_data():
    global sum_temp_1, sum_temp_2, reset_cnt_1, reset_cnt_2, FT_data
    # reset audio
    sum_temp_1 = 0
    sum_temp_2 = 0
    reset_cnt_1 = 0
    reset_cnt_2 = 0

    with ft_lock:
        FT_data = np.zeros_like(FT_data)  
    if daq_thread is not None:
        daq_thread.reset_offset()       
    print("Reset all data (audio + force).")


def close_app():
    global stop_flag, close_flag, app, p, stream1, stream2, th1, th2, timer
    close_flag = 1
    stop_flag = True  
    try:
        if th1.is_alive():
            th1.join()
        if th2.is_alive():
            th2.join()

        # Dừng DAQ thread trước khi đóng file
        if daq_thread is not None:
            daq_thread.stop()
            daq_thread.join()  # Đợi thread kết thúc

        stream1.close()
        stream2.close()
        p.terminate()

        file_1.close()
        file_2.close()
        file_fz.close()

        timer.stop()
        print('Program closed successfully.')
    except Exception as e:
        print(f"Error while closing: {e}")
    finally:
        app.quit()
        sys.exit()


control_widget = pg.LayoutWidget()
resetbtn = QPushButton("Reset")
resetbtn.clicked.connect(reset_data)
control_widget.addWidget(resetbtn, row=0, col=0)

closebtn = QPushButton("Close")
closebtn.clicked.connect(close_app)
control_widget.addWidget(closebtn, row=1, col=0)

d1.addWidget(control_widget)

filterL1 = filterClass.lowPass(2, T, 2)
filterL2 = filterClass.lowPass(2, T, 2)

setup_force_plots()
setup_plots()

timer = QTimer()
timer.timeout.connect(update)
timer.start(0)

th1 = threading.Thread(name='audio_process_1', target=audio_process_1)
th2 = threading.Thread(name='audio_process_2', target=audio_process_2)
try:
    daq_thread = DAQThread()
    daq_thread.start()
except Exception as e:
    print("Không khởi động được DAQ. Tiếp tục chỉ với âm thanh.")
    print(e)
    daq_thread = None
run_thread()

win.show()
sys.exit(app.exec_())