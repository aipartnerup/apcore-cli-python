"""text.wordcount — Count words, characters, and lines."""

from pydantic import BaseModel


class Input(BaseModel):
    text: str


class Output(BaseModel):
    characters: int
    words: int
    lines: int


class TextWordCount:
    """Count words, characters, and lines in a text string."""

    input_schema = Input
    output_schema = Output
    description = "Count words, characters, and lines in a text string"

    def execute(self, inputs, context=None):
        text = inputs["text"]
        return {
            "characters": len(text),
            "words": len(text.split()),
            "lines": len(text.split("\n")),
        }
