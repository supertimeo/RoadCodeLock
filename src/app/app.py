import json
import sys
import random

from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QMainWindow, QWidget, QApplication, QStackedWidget, QLabel, QHBoxLayout, QVBoxLayout, QCheckBox, QPushButton

from common.paths import assets_folder_path
from models.question_model import Question, SubQuestion


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        with open(assets_folder_path / "dataset.json", "r") as f:
            self.dataset = [Question(**question) for question in json.load(f)]

        self.init_ui()

        self.num_question = 0

        self.set_question()

    def init_media_widget(self):
        self.media_layout = QHBoxLayout(self.central_widget)
        self.central_layout.addLayout(self.media_layout)

        self.media = QStackedWidget()
        self.media_layout.addWidget(self.media)

        self.media_image = QLabel(self)
        self.media.addWidget(self.media_image)

        self.media_watch = QVideoWidget(self)
        self.media.addWidget(self.media_watch)

        self.media_watch_player = QMediaPlayer()
        self.media_watch_player.setVideoOutput(self.media_watch)

        self.media_watch_audio_output = QAudioOutput()
        self.media_watch_player.setAudioOutput(self.media_watch_audio_output)
        self.media_watch_audio_output.setVolume(1.0)

    def init_ui(self):
        self.setWindowTitle("RoadCodeLock")
        self.showFullScreen()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.central_layout = QVBoxLayout()
        self.central_widget.setLayout(self.central_layout)

        self.init_media_widget()

        self.question_label = QLabel(self)
        self.central_layout.addWidget(self.question_label)

        self.sub_questions_layout = QHBoxLayout()
        self.central_layout.addLayout(self.sub_questions_layout)

        self.sub_question_1_layout = QVBoxLayout()
        self.sub_questions_layout.addLayout(self.sub_question_1_layout)
        self.sub_question_2_layout = QVBoxLayout()
        self.sub_questions_layout.addLayout(self.sub_question_2_layout)

        self.sub_question_1_label = QLabel(self)
        self.sub_question_1_layout.addWidget(self.sub_question_1_label)
        self.sub_question_2_label = QLabel(self)
        self.sub_question_2_layout.addWidget(self.sub_question_2_label)

        self.sub_question_1_choices_layout = QVBoxLayout()
        self.sub_question_1_layout.addLayout(self.sub_question_1_choices_layout)
        self.sub_question_2_choices_layout = QVBoxLayout()
        self.sub_question_2_layout.addLayout(self.sub_question_2_choices_layout)

        self.sub_question_1_choices: list[tuple[QCheckBox, bool]] = []
        self.sub_question_2_choices: list[tuple[QCheckBox, bool]] = []

        self.explanation_label = QLabel(self)
        self.explanation_label.hide()
        self.central_layout.addWidget(self.explanation_label)

        self.buttons = QStackedWidget()
        self.central_layout.addWidget(self.buttons)

        self.validate_button = QPushButton(self)
        self.validate_button.setText("Validate")
        self.validate_button.clicked.connect(self.validate)
        self.buttons.addWidget(self.validate_button)

        self.next_button = QPushButton()
        self.next_button.setText("Next")
        self.next_button.clicked.connect(self.set_question)
        self.buttons.addWidget(self.next_button)

        self.close_button = QPushButton(self)
        self.close_button.setText("Close")
        self.close_button.clicked.connect(self.close)
        self.buttons.addWidget(self.close_button)

        self.buttons.setCurrentWidget(self.validate_button)

    def set_media(self, question: Question):
        path = assets_folder_path / "uniques_medias" / question.question_media_name
        if question.question_media_is_image:
            self.media_image.setPixmap(QPixmap(path))
            self.media.setCurrentWidget(self.media_image)
        else:
            self.media_watch_player.setSource(QUrl.fromLocalFile(path))
            self.media.setCurrentWidget(self.media_watch)

    @staticmethod
    def set_question_text(question_text: str | None, question_label: QLabel):
        if question_text is not None:
            question_label.show()
            question_label.setText(question_text)
        else:
            question_label.hide()

    @staticmethod
    def set_sub_question(sub_question: SubQuestion, sub_question_label: QLabel, sub_question_choices_layout: QVBoxLayout, sub_question_choices: list[tuple[QCheckBox, bool]]):
        for choice in sub_question_choices:
            sub_question_choices_layout.removeWidget(choice[0])
            choice[0].deleteLater()
        sub_question_choices.clear()

        if sub_question.sub_question is not None:
            sub_question_label.show()
            sub_question_label.setText(sub_question.sub_question)

            for choice in sub_question.choices:
                choice_checkbox = QCheckBox(choice.choice)
                sub_question_choices_layout.addWidget(choice_checkbox)
                sub_question_choices.append((choice_checkbox, choice.is_correct))
        else:
            sub_question_label.hide()

    def set_question(self):
        self.explanation_label.hide()

        question = random.choice(self.dataset)
        self.set_media(question)
        self.set_question_text(question.question_title, self.question_label)

        self.set_sub_question(question.sub_questions[0], self.sub_question_1_label, self.sub_question_1_choices_layout, self.sub_question_1_choices)
        self.set_sub_question(question.sub_questions[1], self.sub_question_2_label, self.sub_question_2_choices_layout, self.sub_question_2_choices)

        self.explanation_label.setText(question.explanations)

        self.buttons.setCurrentWidget(self.validate_button)

        self.dataset.remove(question)

        self.num_question += 1

    @staticmethod
    def validate_choices(sub_question_choices: list[tuple[QCheckBox, bool]]):
        for choice in sub_question_choices:
            if choice[1]:
                choice[0].setText(f"{choice[0].text()} ✔")

    def validate(self):
        self.validate_choices(self.sub_question_1_choices)
        self.validate_choices(self.sub_question_2_choices)
        self.explanation_label.show()
        self.buttons.setCurrentWidget(self.close_button if self.num_question >= 3 else self.next_button)


def main():
    app = QApplication(sys.argv)

    window = Window()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()