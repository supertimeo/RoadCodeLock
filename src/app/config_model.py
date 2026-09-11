from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel


class Config(BaseModel):
    nb_questions: int

    @classmethod
    def load_from_yml(cls, config_file_path: Path) -> Self:
        with open(config_file_path, "r") as f:
            return cls(**yaml.safe_load(f))

    def save_to_yml(self, config_file_path: Path) -> None:
        with open(config_file_path, "w") as f:
            yaml.dump(self.model_dump(), f)