import argparse

from pydantic.dataclasses import dataclass

from common.init_logger import init_logger


@dataclass(frozen=True)
class InitializationData:
    quizz_url: str


def init_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser(description="Scrape quizzes and explanations")
    arg_parser.add_argument("quizz_url", type=str, help="URL of the quizz")
    return arg_parser.parse_args()


def init() -> InitializationData:
    args = init_args()
    init_logger("scraper")
    return InitializationData(quizz_url=args.quizz_url)