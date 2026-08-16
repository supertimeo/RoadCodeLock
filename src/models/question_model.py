from pydantic import BaseModel, ConfigDict


class SubQuestionChoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    choice: str
    is_correct: bool


class SubQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    sub_question: str | None
    choices: tuple[SubQuestionChoice, ...]


class Question(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_media_name: str
    question_media_is_image: bool
    question_title: str | None
    sub_questions: tuple[SubQuestion, ...]
    explanations: str