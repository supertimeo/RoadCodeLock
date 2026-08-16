import argparse
import json
import re
import sys
import time
from enum import StrEnum
from pathlib import Path
from typing import cast, TYPE_CHECKING
from uuid import uuid4

from loguru import logger
from playwright.sync_api import sync_playwright, Page, TimeoutError
from pydantic.dataclasses import dataclass
from selectolax.parser import HTMLParser, Node

if TYPE_CHECKING:
    from loguru import Record

from models.question_model import Question, SubQuestion, SubQuestionChoice

scripts_folder_path = Path(__file__).resolve().parent / "scripts"

log_folder_path = Path(__file__).resolve().parent.parent.parent / "logs" / "scraper"

image_fetcher_script = (scripts_folder_path / "image_fetcher.js").read_text()
watch_fetcher_script = (scripts_folder_path / "watch_fetcher.js").read_text()

class ScraperError(Exception):
    pass


class NavigationError(ScraperError):
    pass


class ElementNotFoundError(NavigationError):
    pass


class ParsingError(ScraperError):
    pass


class FormNotFoundError(ParsingError):
    pass


class ExplanationsNotFoundError(ParsingError):
    pass


class MediaExtractionError(ScraperError):
    pass


class MediaSaveError(ScraperError):
    pass


@dataclass(frozen=True)
class InitializationData:
    quizz_url: str


class LoggingLevels(StrEnum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def extract_question_data(page: Page) -> Question:
    page_locator = page.locator("iframe[title=\"Je repasse le code\"]").content_frame
    quizz_locator = page_locator.locator("div#quizz-container")
    tree = HTMLParser(quizz_locator.inner_html())

    question_content_div = tree.css_first("div.question_content")
    if question_content_div is None:
        raise ElementNotFoundError("Failed to find 'div.question_content' in quiz page")

    time.sleep(0.5)

    for sub_question_div in quizz_locator.locator("div.question_content > form#questions").locator("div[id]").all():
        if not re.match(r"question-\d+", cast(str, sub_question_div.get_attribute("id"))) or sub_question_div.locator("p").count() <= 0:
            continue
        sub_question_div.locator("ul > li").first.click()

    time.sleep(0.5)

    quizz_locator.locator("div.question_content button#button-resultat").click()

    media_container_locator = quizz_locator.locator("div#media-container")

    try:
        if (question_img_locator := media_container_locator.locator("img#question-img")).count():
            question_media = question_img_locator.evaluate(image_fetcher_script)
            question_media_name = f"{uuid4().hex}.webp"
            is_img = True
        else:
            # noinspection bad-argument-type
            question_media = media_container_locator.locator("video#video").evaluate(watch_fetcher_script)
            question_media_name = f"{uuid4().hex}.webm"
            is_img = False
    except Exception as e:
        raise MediaExtractionError("Failed to extract media (image or video) from quiz page") from e

    try:
        with open(f"assets/medias/{question_media_name}", "wb") as f:
            f.write(bytes(question_media))
    except Exception as e:
        raise MediaSaveError(f"Failed to save media file: {question_media_name}") from e

    try:
        question_title_div = question_content_div.css_first("div.questiontitle")

        form_element = question_content_div.css_first("form#questions")
        if form_element is None:
            raise FormNotFoundError("Failed to find form#questions element")

        explanations_div = question_content_div.css_first("div#explications > p")
        if explanations_div is None:
            raise ExplanationsNotFoundError("Failed to find explanations div#explications > p")

        # noinspection unresolved-references
        question_data = Question(
            question_media_name = question_media_name,
            question_media_is_image = is_img,
            question_title = question_title_div.text().replace(' ', ' ').strip() if question_title_div is not None else None,
            sub_questions = [
                SubQuestion(
                    sub_question = sub_question_div.css_first("p").text().replace(' ', ' ').strip(),
                    choices = [
                        SubQuestionChoice(
                            choice = choice_li.css_first("div > label").text().replace(' ', ' ').strip(),
                            is_correct = bool(int(cast(str, choice_li.css_first("span").attributes.get("data-valid"))))
                        )
                        for choice_li in sub_question_div.css("ul > li")
                    ]
                ) for sub_question_div in form_element.css("div[id]") if re.match(r"question-\d+", cast(str, sub_question_div.attributes.get("id"))) and sub_question_div.css_first("p") is not None
            ],
                explanations = explanations_div.text()
        )
    except Exception as e:
        raise ParsingError("Failed to parse question data from quiz page") from e

    time.sleep(0.5)

    for i in range(3):
        try:
            quizz_locator.locator("div.question_content button#button-continue").click()
            break
        except TimeoutError as e:
            if i == 2:
                raise ElementNotFoundError("Failed to click continue button after 3 attempts") from e

            logger.warning("Failed to click the continue button.")
            continue

    return question_data


def log_patcher(record: Record):
    """Enrichit un enregistrement de log avec des informations de localisation et de thread.
    Cette fonction prépare les champs supplémentaires utilisés par le formatteur de logs.

    Args:
        record (Record): L'enregistrement de log à modifier, contenant les informations
            de contexte et les champs extra.
    """
    class_name = record["extra"].get("class_name")
    record["extra"]["location"] = f"{record['file'].name}{f":{class_name}" if class_name is not None else ""}{f":{record['function']}" if record['function'] != "<module>" else ""}:{record['line']}"
    record["extra"]["thread_info"] = f"{record["thread"].name} ({record["thread"].id})"


def log_format(_record: Record) -> str:
    """Construit une chaîne de formatage pour les messages de log enrichis.
    Cette fonction définit la présentation des informations de temps, niveau, localisation, thread et message.

    Args:
        _record (Record): L'enregistrement de log à formatter, utilisé pour alimenter les champs du gabarit.

    Returns:
        str: Le gabarit de formatage à utiliser par Loguru pour rendre les messages de log.
    """
    return (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "<level>{level: <8}</level> | "
        "{extra[location]: <50} | "
        "{extra[thread_info]: <20} - "
        "{message}\n"
        "{exception}"
    )


def init_logger():
    """Initialise et configure le système de journalisation de l'application crawler TUI.
    Cette fonction prépare les fichiers de logs, les niveaux personnalisés et le sink Textual pour l'affichage dans l'interface.
    """

    # création du logger
    logger.remove()

    logger.configure(patcher=log_patcher)

    logger.add(sys.stdout, level=LoggingLevels.TRACE, format=log_format)
    logger.add(log_folder_path / "latest" / "latest.log", rotation="1 MB", retention="7 days", compression="zip", level=LoggingLevels.INFO,
               format=log_format)
    logger.add(log_folder_path / "error" / "error.log", rotation="200 MB", retention="7 days", compression="zip", level=LoggingLevels.ERROR,
               format=log_format, backtrace=True, diagnose=True)
    logger.add(log_folder_path / "trace" / "trace.log", rotation="10 GB", retention="7 days", compression="zip", level=LoggingLevels.TRACE,
               format=log_format)

    logger.info("Logger initialized")


def init_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(description="Scrape quizzes and explanations")
    arg_parser.add_argument("quizz_url", type=str, help="URL of the quizz")
    return arg_parser.parse_args()


def init() -> InitializationData:
    args = init_args()
    init_logger()
    return InitializationData(quizz_url=args.quizz_url)


@logger.catch(message="An unexpected error occurred during scraping")
def main():
    initialization_data = init()

    dataset: list[Question] = []

    with sync_playwright() as p:
        logger.trace("openning browser")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        logger.trace(f"opening url: {initialization_data.quizz_url}")
        page.goto(initialization_data.quizz_url)

        page.locator("div#footer_tc_privacy button#footer_tc_privacy_button").click()

        # Attendre que le contenu soit généré
        page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#choice-1.choice[role='button']").click()

        try:
            while True:
                page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#rules-entrainement button.button.reverse").click()

                dataset.extend(extract_question_data(page) for _ in range(10))

                page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#screen-gameover > ul#gameover-buttons-list > li").nth(2).locator("button").click()
        except KeyboardInterrupt:
            pass

        browser.close()

    with open("assets/dataset.json", "w", encoding='utf-8') as f:
        json.dump([question.model_dump() for question in dataset], f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()