import sys
import random
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

# --- DANH SÁCH TỪ KHÓA ---
WORD_LIST = [
    # Danh sách cũ (75 từ)
    "Ăn mì gói", "Thể dục nhịp điệu", "Không thở được", "Điện giật", "Cầu hôn",
    "High five", "Make up", "Mang thai", "Múa bale", "Nhõng nhẽo", "Đi catwalk",
    "Đấm bốc", "Hát karaoke", "Cưỡi ngựa", "Đau bụng", "Câu cá", "Tắm mưa",
    "Đeo khẩu trang", "Hôn nhau", "Lắc vòng", "Hoa hậu", "Bập bênh", "Xích đu",
    "Bước hụt", "Ăn kem", "Say rượu", "Nhổ răng", "Trượt patin", "Nhảy dây",
    "Lợn quay", "Nhảy dù", "Nhắn tin", "Gọi điện", "Hít thở", "Tập yoga",
    "Tập gym", "Ăn kẹo mút", "Nước nóng", "Khóc lóc", "Sống ảo", "Nhảy zumba",
    "Con bò cười", "Nhảy lò cò", "Thả diều", "Đánh nhau", "Lạng lách đánh võng",
    "Hút thuốc", "Ngất xỉu", "Khỉ cười", "Bịt mắt bắt dê", "Con chó", "Con mèo",
    "Con gà", "Con vịt", "Con lợn", "Con ngựa", "Con voi", "Con khỉ", "Con hổ",
    "Sư tử", "Hươu cao cổ", "Chim cánh cụt", "Kangaroo", "Cá mập", "Cá heo",
    "Bạch tuộc", "Con cua", "Con rắn", "Con ếch", "Con thỏ", "Con rùa",
    "Con bướm", "Con ong", "Gấu trúc", "Đại bàng",

    # --- BỔ SUNG ĐỂ ĐỦ 100 TỪ ---
    "Bác sĩ",
    "Giáo viên",
    "Ca sĩ",
    "Lính cứu hỏa",
    "Đầu bếp",
    "Siêu nhân",
    "Cảnh sát giao thông",
    "Chơi bóng đá",
    "Bơi lội",
    "Vẽ tranh",
    "Trồng cây",
    "Rửa xe",
    "Đi siêu thị",
    "Cắt tóc",
    "Tủ lạnh",
    "Máy giặt",
    "Quạt trần",
    "Bàn là",
    "Robot hút bụi",
    "Ăn pizza",
    "Uống trà sữa",
    "Leo núi",
    "Chơi game",
    "Xem phim ma",
    "Trượt tuyết"
]


class CharadesGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NHÌN HÀNH ĐỘNG ĐOÁN TỪ")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: #f0f4f8;")

        self.team1_score = 0
        self.team2_score = 0
        self.current_team = 1
        self.game_running = False
        self.remaining_words = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.time_left = 0
        self.turn_duration = 600  # Bạn có thể chỉnh thời gian mỗi lượt ở đây

        self.init_ui()
        self.reset_game()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Giao diện không thay đổi, giữ nguyên phần này ---
        score_layout = QHBoxLayout()
        self.team1_score_label = QLabel(f"ĐỘI 1: {self.team1_score}")
        self.team1_score_label.setFont(QFont("Montserrat", 18, QFont.Bold))
        self.team1_score_label.setStyleSheet("color: #2c3e50; padding: 10px; background-color: #ecf0f1; border-radius: 10px;")
        self.team1_score_label.setAlignment(Qt.AlignCenter)

        self.team2_score_label = QLabel(f"ĐỘI 2: {self.team2_score}")
        self.team2_score_label.setFont(QFont("Montserrat", 18, QFont.Bold))
        self.team2_score_label.setStyleSheet("color: #2c3e50; padding: 10px; background-color: #ecf0f1; border-radius: 10px;")
        self.team2_score_label.setAlignment(Qt.AlignCenter)

        score_layout.addWidget(self.team1_score_label)
        score_layout.addStretch()
        score_layout.addWidget(self.team2_score_label)

        self.word_display = QLabel("Bấm 'BẮT ĐẦU LƯỢT' để chơi!")
        self.word_display.setFont(QFont("SVN-Gotham", 40, QFont.Bold))
        self.word_display.setAlignment(Qt.AlignCenter)
        self.word_display.setWordWrap(True)
        self.word_display.setStyleSheet("""
            background-color: #ffffff; border: 3px solid #3498db; 
            border-radius: 15px; padding: 25px; color: #2c3e50; min-height: 150px;
        """)

        info_layout = QHBoxLayout()
        self.turn_label = QLabel(f"LƯỢT CỦA: ĐỘI {self.current_team}")
        self.turn_label.setFont(QFont("Montserrat", 16, QFont.Medium))
        self.turn_label.setStyleSheet("color: #34495e;")

        self.timer_label = QLabel(f"THỜI GIAN: {self.turn_duration}s")
        self.timer_label.setFont(QFont("Montserrat", 18, QFont.Bold))
        self.timer_label.setStyleSheet("color: #e74c3c; background-color: #ffebee; border-radius: 8px; padding: 5px 15px;")
        self.timer_label.setAlignment(Qt.AlignRight)

        info_layout.addWidget(self.turn_label)
        info_layout.addStretch()
        info_layout.addWidget(self.timer_label)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)

        self.start_button = QPushButton("BẮT ĐẦU LƯỢT")
        self.start_button.setFont(QFont("Montserrat", 16, QFont.Bold))
        self.start_button.setMinimumHeight(60)
        self.start_button.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; border-radius: 12px; padding: 10px 20px; border: none; }
            QPushButton:hover { background-color: #27ae60; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.start_button.clicked.connect(self.start_turn)

        self.correct_button = QPushButton("ĐÚNG (+1)")
        self.correct_button.setFont(QFont("Montserrat", 16, QFont.Bold))
        self.correct_button.setMinimumHeight(60)
        self.correct_button.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; border-radius: 12px; padding: 10px 20px; border: none; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.correct_button.clicked.connect(self.correct_guess)

        self.skip_button = QPushButton("BỎ QUA")
        self.skip_button.setFont(QFont("Montserrat", 16, QFont.Bold))
        self.skip_button.setMinimumHeight(60)
        self.skip_button.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; border-radius: 12px; padding: 10px 20px; border: none; }
            QPushButton:hover { background-color: #e67e22; }
            QPushButton:disabled { background-color: #bdc3c7; }
        """)
        self.skip_button.clicked.connect(self.skip_word)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.correct_button)
        control_layout.addWidget(self.skip_button)

        self.reset_button = QPushButton("CHƠI LẠI TỪ ĐẦU")
        self.reset_button.setFont(QFont("Montserrat", 14))
        self.reset_button.setMinimumHeight(45)
        self.reset_button.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; border-radius: 10px; padding: 8px 15px; border: none; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        self.reset_button.clicked.connect(self.reset_game)

        main_layout.addLayout(score_layout)
        main_layout.addLayout(info_layout)
        main_layout.addWidget(self.word_display, 1)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.reset_button, 0, Qt.AlignRight)

        self.setLayout(main_layout)

    def reset_game(self):
        self.team1_score = 0
        self.team2_score = 0
        self.current_team = 1
        self.update_scores()
        self.update_turn_label()

        self.remaining_words = WORD_LIST[:]
        random.shuffle(self.remaining_words)

        self.word_display.setText(f"Sẵn sàng!\nLượt của ĐỘI {self.current_team}")
        self.timer_label.setText(f"THỜI GIAN: {self.turn_duration}s")
        self.timer.stop()
        self.game_running = False
        self.set_ui_state('initial')

    def start_turn(self):
        if self.game_running:
            return
        if not self.remaining_words:
            self.show_end_game_message("Đã hết từ để đoán!")
            return

        self.game_running = True
        self.time_left = self.turn_duration
        self.timer_label.setText(f"THỜI GIAN: {self.time_left}s")
        self.timer.start(1000)

        self.next_word()
        self.set_ui_state('running')

    # --- THAY ĐỔI LOGIC CHÍNH NẰM Ở ĐÂY ---
    def end_turn(self):
        """Kết thúc lượt chơi hiện tại và quyết định bước tiếp theo."""
        self.game_running = False
        self.timer.stop()

        # Kiểm tra xem lượt của đội nào vừa kết thúc
        if self.current_team == 1:
            # Lượt của Đội 1 vừa xong, chuẩn bị cho Đội 2
            self.current_team = 2
            self.update_turn_label()
            self.word_display.setText(f"HẾT GIỜ!\nTiếp theo là lượt của ĐỘI {self.current_team}")
            self.timer_label.setText(f"THỜI GIAN: {self.turn_duration}s")
            self.set_ui_state('initial')  # Cho phép Đội 2 nhấn nút "Bắt đầu"
        else: # self.current_team == 2
            # Lượt của Đội 2 vừa xong, kết thúc toàn bộ ván chơi
            self._finish_match()

    def _finish_match(self):
        """Hàm này được gọi khi cả 2 đội đã chơi xong."""
        # Vô hiệu hóa các nút chơi game
        self.start_button.setEnabled(False)
        self.correct_button.setEnabled(False)
        self.skip_button.setEnabled(False)

        # Hiển thị thông báo kết quả cuối cùng
        self.show_end_game_message("Đã hoàn thành các lượt chơi!")
    # --- KẾT THÚC PHẦN THAY ĐỔI ---

    def next_word(self):
        if not self.remaining_words:
            self.word_display.setText("HẾT TỪ!")
            self.end_turn() # Tự động kết thúc lượt nếu hết từ
            return

        word = self.remaining_words.pop(0)
        self.word_display.setText(word.upper())

    def correct_guess(self):
        if not self.game_running:
            return
        if self.current_team == 1:
            self.team1_score += 1
        else:
            self.team2_score += 1
        self.update_scores()
        self.next_word()

    def skip_word(self):
        if not self.game_running:
            return
        self.next_word()

    def update_scores(self):
        self.team1_score_label.setText(f"ĐỘI 1: {self.team1_score}")
        self.team2_score_label.setText(f"ĐỘI 2: {self.team2_score}")

    def update_turn_label(self):
        self.turn_label.setText(f"LƯỢT CỦA: ĐỘI {self.current_team}")

    def update_timer(self):
        self.time_left -= 1
        self.timer_label.setText(f"THỜI GIAN: {self.time_left}s")

        if self.time_left <= 10:
            self.timer_label.setStyleSheet("color: #c0392b; background-color: #ffebee; border-radius: 8px; padding: 5px 15px;")
        else:
            self.timer_label.setStyleSheet("color: #e74c3c; background-color: #ffebee; border-radius: 8px; padding: 5px 15px;")

        if self.time_left <= 0:
            self.end_turn()

    def set_ui_state(self, state):
        if state == 'initial':
            self.start_button.setEnabled(True)
            self.correct_button.setEnabled(False)
            self.skip_button.setEnabled(False)
        elif state == 'running':
            self.start_button.setEnabled(False)
            self.correct_button.setEnabled(True)
            self.skip_button.setEnabled(True)

    def show_end_game_message(self, message):
        """Hàm này bây giờ sẽ là hàm công bố kết quả cuối cùng."""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("TRÒ CHƠI KẾT THÚC")
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #ecf0f1; }
            QMessageBox QLabel { color: #2c3e50; font-size: 14px; }
            QMessageBox QPushButton { background-color: #3498db; color: white; border-radius: 5px; padding: 5px 10px; }
            QMessageBox QPushButton:hover { background-color: #2980b9; }
        """)

        winner_text = ""
        if self.team1_score > self.team2_score:
            winner_text = "ĐỘI 1 chiến thắng rực rỡ!"
        elif self.team2_score > self.team1_score:
            winner_text = "ĐỘI 2 chiến thắng đầy kịch tính!"
        else:
            winner_text = "Hai đội HÒA NHAU!"

        msg_box.setText(f"🎉 {message}\n\n🏆 Kết quả chung cuộc: {winner_text}")
        msg_box.setInformativeText("Bạn có muốn chơi lại từ đầu không?")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        return_value = msg_box.exec_()
        if return_value == QMessageBox.Yes:
            self.reset_game()
        else:
            QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    game = CharadesGame()
    game.show()
    sys.exit(app.exec_())