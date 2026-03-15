"""text.reverse — Reverse a string."""

from pydantic import BaseModel


class Input(BaseModel):
    text: str


class Output(BaseModel):
    result: str


class TextReverse:
    """Reverse a string character by character."""

    input_schema = Input
    output_schema = Output
    description = "Reverse a string character by character"

    def execute(self, inputs, context=None):
        return {"result": inputs["text"][::-1]}
