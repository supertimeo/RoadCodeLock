import json
import random
import sys
from typing import Literal, cast

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QUrl
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config_model import Config
from common.paths import assets_folder_path, configs_folder_path
from models.question_model import Question, SubQuestion


class ChoiceCard(QCheckBox):
    """Case à cocher dont toute la surface rectangulaire est cliquable."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def hitButton(self, pos: QPoint) -> bool:
        return self.rect().contains(pos)


class AspectRatioImageWidget(QWidget):
    """Widget de rendu d'image préservant le ratio centré."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(0, 0)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def paintEvent(self, event):
        if not self._pixmap or self._pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # QSize.scaled ne prend que la taille cible et le mode de ratio
        scaled_size = self._pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        target_rect = QRect(x, y, scaled_size.width(), scaled_size.height())

        painter.drawPixmap(target_rect, self._pixmap)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        with open(assets_folder_path / "dataset.json", "r", encoding="utf-8") as f:
            self.dataset = [Question(**q) for q in json.load(f)]

        self.config = Config.load_from_yml(configs_folder_path / "app_config.yml")
        self.num_question = 0
        self.total_target = self.config.nb_questions

        # Récupération du thème enregistré (défaut : "dark")
        self.current_theme: Literal["dark", "light"] = cast(
            Literal["dark", "light"],
            getattr(self.config, "theme", "dark") or "dark"
        )

        self.init_ui()
        self.apply_theme(self.current_theme, save_config=False) # type: ignore
        self.set_question()

    def apply_theme(self, theme_name: Literal["dark", "light"], save_config: bool = True):
        """Applique la feuille de style correspondant au thème et met à jour l'UI."""
        self.current_theme = theme_name
        qss_file = assets_folder_path / "styles" / f"{theme_name}.qss"

        if qss_file.exists():
            with open(qss_file, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        # Mise à jour de l'état et de l'icône du bouton
        if hasattr(self, "theme_toggle_btn"):
            if theme_name == "dark":
                self.theme_toggle_btn.setText("🌙 Sombre")
            else:
                self.theme_toggle_btn.setText("☀️ Clair")

        if save_config:
            self.save_theme_to_config(theme_name)

    def toggle_theme(self):
        """Alterne entre le thème sombre et le thème clair."""
        next_theme: Literal["dark", "light"] = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(next_theme, save_config=True)

    def save_theme_to_config(self, theme_name: Literal["dark", "light"]):
        """Sauvegarde le thème sélectionné dans app_config.yml."""
        self.config.theme = theme_name
        config_file = configs_folder_path / "app_config.yml"
        self.config.save_to_yml(config_file)

    def init_ui(self):
        self.setWindowTitle("RoadCodeLock")

        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        root_layout = QVBoxLayout(self.central_widget)
        root_layout.setContentsMargins(18, 8, 18, 8)
        root_layout.setSpacing(6)

        # 1. Header (Fixe en haut)
        self.init_header(root_layout)

        # 2. Média panoramique dynamique (Prend tout l'espace disponible)
        self.init_media_section(root_layout)

        # 3. Questionnaire (Taille naturelle selon le nombre de choix)
        self.init_questions_section(root_layout)

        # 4. Explication (Taille pré-réservée anti-décalage)
        self.init_explanation_section(root_layout)

        # 5. Footer / Bouton Valider (Ancré en bas)
        self.init_footer_actions(root_layout)

        self.showFullScreen()

    def init_header(self, parent_layout: QVBoxLayout):
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(10, 3, 10, 3)
        header_layout.setSpacing(10)

        title = QLabel("ROADCODE LOCK")
        title.setObjectName("AppTitle")

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, self.total_target)
        self.progress_bar.setValue(0)

        self.counter_label = QLabel(f"Question 1 / {self.total_target}")
        self.counter_label.setObjectName("CounterBadge")

        # Bouton Toggle Thème
        self.theme_toggle_btn = QPushButton("🌙 Sombre")
        self.theme_toggle_btn.setObjectName("ThemeToggle")
        self.theme_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)

        header_layout.addWidget(title)
        header_layout.addWidget(self.progress_bar, stretch=1)
        header_layout.addWidget(self.counter_label)
        header_layout.addWidget(self.theme_toggle_btn)

        parent_layout.addWidget(header_card, stretch=0)

    def init_media_section(self, parent_layout: QVBoxLayout):
        self.media_container = QFrame()
        self.media_container.setObjectName("MediaContainer")
        self.media_container.setMinimumSize(0, 0)
        self.media_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container_layout = QVBoxLayout(self.media_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.media_stack = QStackedWidget()
        self.media_stack.setMinimumSize(0, 0)
        self.media_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_layout.addWidget(self.media_stack)

        self.media_image = AspectRatioImageWidget()
        self.media_stack.addWidget(self.media_image)

        self.media_watch = QVideoWidget()
        self.media_watch.setMinimumSize(0, 0)
        self.media_watch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.media_stack.addWidget(self.media_watch)

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.media_watch)
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        # Stretch=1 : absorbe tout l'espace libre restant
        parent_layout.addWidget(self.media_container, stretch=1)

    def init_questions_section(self, parent_layout: QVBoxLayout):
        self.questions_wrapper = QWidget()
        self.questions_wrapper.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        questions_layout = QVBoxLayout(self.questions_wrapper)
        questions_layout.setContentsMargins(0, 0, 0, 0)
        questions_layout.setSpacing(4)

        # Titre de la question
        self.question_title_label = QLabel()
        self.question_title_label.setObjectName("QuestionTitle")
        self.question_title_label.setWordWrap(True)
        questions_layout.addWidget(self.question_title_label)

        # Sous-questions A & B
        self.sub_questions_container = QHBoxLayout()
        self.sub_questions_container.setSpacing(10)
        self.sub_questions_container.setContentsMargins(0, 0, 0, 0)
        questions_layout.addLayout(self.sub_questions_container)

        self.card_1, self.sub_q1_label, self.sub_q1_choices_layout = self.create_sub_question_card()
        self.card_2, self.sub_q2_label, self.sub_q2_choices_layout = self.create_sub_question_card()

        self.sub_questions_container.addWidget(self.card_1, stretch=1)
        self.sub_questions_container.addWidget(self.card_2, stretch=1)

        parent_layout.addWidget(self.questions_wrapper, stretch=0)

        self.sub_q1_choices: list[tuple[ChoiceCard, bool]] = []
        self.sub_q2_choices: list[tuple[ChoiceCard, bool]] = []

    @staticmethod
    def create_sub_question_card():
        card = QFrame()
        card.setProperty("class", "sub-card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(3)

        label = QLabel()
        label.setObjectName("SubQuestionLabel")
        label.setWordWrap(True)
        layout.addWidget(label)

        choices_layout = QVBoxLayout()
        choices_layout.setSpacing(3)
        layout.addLayout(choices_layout)

        return card, label, choices_layout

    def init_explanation_section(self, parent_layout: QVBoxLayout):
        self.explanation_card = QFrame()
        self.explanation_card.setObjectName("ExplanationBox")

        # Réservation d'espace pour éviter tout décalage visuel
        sp = self.explanation_card.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        sp.setVerticalPolicy(QSizePolicy.Policy.Preferred)
        sp.setRetainSizeWhenHidden(True)
        self.explanation_card.setSizePolicy(sp)

        expl_layout = QVBoxLayout(self.explanation_card)
        expl_layout.setContentsMargins(8, 4, 8, 4)
        expl_layout.setSpacing(2)

        expl_header = QLabel("Explication")
        expl_header.setObjectName("ExplanationHeader")
        expl_layout.addWidget(expl_header)

        self.explanation_label = QLabel()
        self.explanation_label.setObjectName("ExplanationText")
        self.explanation_label.setWordWrap(True)
        expl_layout.addWidget(self.explanation_label)

        self.explanation_card.hide()
        parent_layout.addWidget(self.explanation_card, stretch=0)

    def init_footer_actions(self, parent_layout: QVBoxLayout):
        footer = QWidget()
        footer.setObjectName("ActionContainer")
        footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 2)

        self.buttons_stack = QStackedWidget()
        self.buttons_stack.setFixedHeight(34)

        self.validate_button = QPushButton("Valider la réponse")
        self.validate_button.setObjectName("PrimaryButton")
        self.validate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.validate_button.clicked.connect(self.validate)
        self.buttons_stack.addWidget(self.validate_button)

        self.next_button = QPushButton("Question suivante →")
        self.next_button.setObjectName("PrimaryButton")
        self.next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_button.clicked.connect(self.set_question)
        self.buttons_stack.addWidget(self.next_button)

        self.unlock_button = QPushButton("Déverrouiller le PC")
        self.unlock_button.setObjectName("UnlockButton")
        self.unlock_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.unlock_button.clicked.connect(self.close)
        self.buttons_stack.addWidget(self.unlock_button)

        footer_layout.addStretch()
        footer_layout.addWidget(self.buttons_stack)
        footer_layout.addStretch()

        parent_layout.addWidget(footer, stretch=0)

    def set_media(self, question: Question):
        path = assets_folder_path / "uniques_medias" / question.question_media_name
        if question.question_media_is_image:
            self.media_image.set_pixmap(QPixmap(str(path)))
            self.media_stack.setCurrentWidget(self.media_image)
        else:
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.media_stack.setCurrentWidget(self.media_watch)
            self.media_player.play()

    @staticmethod
    def set_sub_question_data(sub_q: SubQuestion, card: QFrame, label: QLabel, choices_layout: QVBoxLayout, choices_list: list):
        for choice_widget, _ in choices_list:
            choices_layout.removeWidget(choice_widget)
            choice_widget.setParent(None)
            choice_widget.deleteLater()
        choices_list.clear()

        if sub_q.sub_question:
            card.show()
            label.setText(sub_q.sub_question)
            for item in sub_q.choices:
                cb = ChoiceCard(item.choice)
                choices_layout.addWidget(cb)
                choices_list.append((cb, item.is_correct))
        else:
            card.hide()

    def set_question(self):
        if not self.dataset:
            self.close()
            return

        self.num_question += 1
        self.counter_label.setText(f"Question {self.num_question} / {self.total_target}")
        self.progress_bar.setValue(self.num_question - 1)

        question = random.choice(self.dataset)

        self.set_media(question)

        if question.question_title:
            self.question_title_label.show()
            self.question_title_label.setText(question.question_title)
        else:
            self.question_title_label.hide()

        self.set_sub_question_data(question.sub_questions[0], self.card_1, self.sub_q1_label, self.sub_q1_choices_layout, self.sub_q1_choices)
        self.set_sub_question_data(question.sub_questions[1], self.card_2, self.sub_q2_label, self.sub_q2_choices_layout, self.sub_q2_choices)

        self.explanation_label.setText(question.explanations or "Aucune explication pour cette question.")
        self.explanation_card.hide()

        self.buttons_stack.setCurrentWidget(self.validate_button)
        self.dataset.remove(question)

    @staticmethod
    def apply_choice_feedback(choices: list[tuple[ChoiceCard, bool]]):
        for checkbox, is_correct in choices:
            checkbox.setEnabled(False)
            user_checked = checkbox.isChecked()

            if is_correct and user_checked:
                checkbox.setProperty("state", "correct")
            elif not is_correct and user_checked:
                checkbox.setProperty("state", "wrong")
            elif is_correct:
                checkbox.setProperty("state", "missed")

            if style := checkbox.style():
                style.unpolish(checkbox)
                style.polish(checkbox)

    def validate(self):
        self.apply_choice_feedback(self.sub_q1_choices)
        self.apply_choice_feedback(self.sub_q2_choices)

        self.progress_bar.setValue(self.num_question)
        self.explanation_card.show()

        if self.num_question >= self.total_target:
            self.buttons_stack.setCurrentWidget(self.unlock_button)
        else:
            self.buttons_stack.setCurrentWidget(self.next_button)


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()