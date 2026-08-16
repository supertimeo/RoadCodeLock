import json
import re
import time
from pathlib import Path
from typing import cast, Any
from uuid import uuid4

from playwright.sync_api import sync_playwright, Page
from selectolax.parser import HTMLParser, Node

QUIZZ_URL = "https://www.securite-routiere.gouv.fr/les-medias/nos-quiz/je-repasse-le-code"

scripts_folder = Path(__file__).resolve().parent / "scripts"

image_fetcher_script = (scripts_folder / "image_fetcher.js").read_text()
watch_fetcher_script = (scripts_folder / "watch_fetcher.js").read_text()

def fetch_data(page: Page) -> dict[str, Any]:
    page_locator = page.locator("iframe[title=\"Je repasse le code\"]").content_frame
    quizz_locator = page_locator.locator("div#quizz-container")
    tree = HTMLParser(quizz_locator.inner_html())

    question_content_div = cast(Node, tree.css_first("div.question_content"))

    time.sleep(0.5)

    for sub_question_div in quizz_locator.locator("div.question_content > form#questions").locator("div[id]").all():
        if not re.match(r"question-\d+", cast(str, sub_question_div.get_attribute("id"))) or sub_question_div.locator("p").count() <= 0:
            continue
        sub_question_div.locator("ul > li").first.click()

    time.sleep(0.5)

    quizz_locator.locator("div.question_content button#button-resultat").click()

    media_container_locator = quizz_locator.locator("div#media-container")

    if (question_img_locator := media_container_locator.locator("img#question-img")).count():
        question_media = question_img_locator.evaluate(image_fetcher_script)
        question_media_name = f"{uuid4().hex}.webp"
        is_img = True
    else:
        # noinspection bad-argument-type
        question_media = media_container_locator.locator("video#video").evaluate(watch_fetcher_script)
        question_media_name = f"{uuid4().hex}.webm"
        is_img = False


    with open(f"assets/medias/{question_media_name}", "wb") as f:
        f.write(bytes(question_media))

    question_title_div = question_content_div.css_first("div.questiontitle")
    # noinspection unresolved-references
    question_data = {
        "question_media_name": question_media_name,
        "question_media_is_img": is_img,
        "question_title": question_title_div.text().replace(' ', ' ').strip() if question_title_div is not None else None,
        "sub_questions": [
            {
                "sub_question": sub_question_div.css_first("p").text().replace(' ', ' ').strip(),
                "choices": [
                    {
                        "choice": choice_li.css_first("div > label").text().replace(' ', ' ').strip(),
                        "is_correct": int(cast(str, choice_li.css_first("span").attributes.get("data-valid")))
                    }
                    for choice_li in sub_question_div.css("ul > li")
                ]
            } for sub_question_div in question_content_div.css_first("form#questions").css("div[id]") if re.match(r"question-\d+", cast(str, sub_question_div.attributes.get("id"))) and sub_question_div.css_first("p") is not None
        ],
        "explanations": question_content_div.css_first("div#explications > p").text()
    }

    time.sleep(0.5)

    quizz_locator.locator("div.question_content button#button-continue").click()

    return question_data

def main():
    dataset = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(QUIZZ_URL)

        # Attendre que le contenu soit généré
        page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#choice-1.choice[role='button']").click()

        try:
            while True:
                page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#rules-entrainement button.button.reverse").click()

                dataset.extend(fetch_data(page) for _ in range(10))

                page.locator("iframe[title=\"Je repasse le code\"]").content_frame.locator("div#screen-gameover > ul#gameover-buttons-list > li").nth(2).locator("button").click()
        except KeyboardInterrupt:
            pass

        browser.close()

    with open("assets/dataset.json", "w", encoding='utf-8') as f:
        json.dump(dataset, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()