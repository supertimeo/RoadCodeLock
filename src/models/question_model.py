from pydantic import BaseModel

class SubQuestionChoice(BaseModel):
    choice: str
    is_correct: bool


class SubQuestion(BaseModel):
    sub_question: str | None
    choices: list[SubQuestionChoice]


class Question(BaseModel):
    question_media_name: str
    question_media_is_image: bool
    question_title: str | None
    sub_questions: list[SubQuestion]
    explanations: str