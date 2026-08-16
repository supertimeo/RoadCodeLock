import asyncio
import json
import re
import time
from asyncio import CancelledError
from itertools import chain
from pathlib import Path
from typing import cast
from uuid import uuid4

from loguru import logger
from playwright.async_api import async_playwright, Page, TimeoutError
from selectolax.parser import HTMLParser

from scraper.bootstrap import init, InitializationData
from scraper.errors import ElementNotFoundError, MediaExtractionError, MediaSaveError, FormNotFoundError, ExplanationsNotFoundError, ParsingError, NavigationError

from models.question_model import Question, SubQuestion, SubQuestionChoice

scripts_folder_path = Path(__file__).resolve().parent / "scripts"

image_fetcher_script = (scripts_folder_path / "image_fetcher.js").read_text()
watch_fetcher_script = (scripts_folder_path / "watch_fetcher.js").read_text()

async def extract_question_data(page: Page) -> Question:
    page_locator = page.locator("iframe[title=\"Je repasse le code\"]").content_frame
    quizz_locator = page_locator.locator("div#quizz-container")
    tree = HTMLParser(await quizz_locator.inner_html())

    question_content_div = tree.css_first("div.question_content")
    if question_content_div is None:
        raise ElementNotFoundError("Failed to find 'div.question_content' in quiz page")

    time.sleep(0.5)

    for sub_question_div in await quizz_locator.locator("div.question_content > form#questions").locator("div[id][data-active='1']").all():
        if not re.match(r"question-\d+", cast(str, await sub_question_div.get_attribute("id"))):
            continue
        await sub_question_div.locator("ul > li").first.click()

    time.sleep(0.5)

    await quizz_locator.locator("div.question_content button#button-resultat").click()

    media_container_locator = quizz_locator.locator("div#media-container")

    try:
        if await (question_img_locator := media_container_locator.locator("img#question-img")).count():
            question_media = await question_img_locator.evaluate(image_fetcher_script)
            question_media_name = f"{uuid4().hex}.webp"
            is_img = True
        else:
            # noinspection bad-argument-type
            question_media = await media_container_locator.locator("video#video").evaluate(watch_fetcher_script)
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
                    sub_question = sub_question_div.css_first("p").text().replace(' ', ' ').strip() if sub_question_div.css_first("p") is not None else None,
                    choices = [
                        SubQuestionChoice(
                            choice = choice_li.css_first("div > label").text().replace(' ', ' ').strip(),
                            is_correct = bool(int(cast(str, choice_li.css_first("span").attributes.get("data-valid"))))
                        )
                        for choice_li in sub_question_div.css("ul > li")
                    ]
                ) for sub_question_div in form_element.css("div[id]") if re.match(r"question-\d+", cast(str, sub_question_div.attributes.get("id")))
            ],
            explanations = explanations_div.text()
        )
    except Exception as e:
        raise ParsingError("Failed to parse question data from quiz page") from e

    time.sleep(0.5)

    for i in range(3):
        try:
            await quizz_locator.locator("div.question_content button#button-continue").click()
            break
        except TimeoutError as e:
            if i == 2:
                raise NavigationError("Failed to click continue button after 3 attempts") from e

            logger.warning("Failed to click the continue button.")
            continue

    return question_data


async def worker(initialization_data: InitializationData, page: Page) -> list[Question]:
    local_dataset: list[Question] = []

    logger.trace(f"opening url: {initialization_data.quizz_url}")
    await page.goto(initialization_data.quizz_url)

    await page.locator("div#footer_tc_privacy button#footer_tc_privacy_button").click()

    # Attendre que le contenu soit généré
    await page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#choice-1.choice[role='button']").click()

    try:
        while True:
            await page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#rules-entrainement button.button.reverse").click()

            for _ in range(10):
                local_dataset.append(await extract_question_data(page))

            await page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#screen-gameover > ul#gameover-buttons-list > li").nth(2).locator("button").click()
    except CancelledError:
        logger.success("worker stoping successfull")
        return local_dataset



@logger.catch(message="An unexpected error occurred during scraping")
async def main():
    initialization_data = init()

    dataset: list[Question] = []

    async with async_playwright() as p:
        logger.trace("openning browser")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        pages = [await context.new_page() for _ in range(initialization_data.num_workers)]
        dataset =  [question async for local_dataset in await asyncio.gather(*(worker(initialization_data, page) for page in pages)) for question in local_dataset]

        await browser.close()

    with open("assets/dataset.json", "w", encoding='utf-8') as f:
        json.dump([question.model_dump() for question in dataset], f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())