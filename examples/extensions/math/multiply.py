"""math.multiply — Multiply two numbers."""

from pydantic import BaseModel


class Input(BaseModel):
    a: int
    b: int


class Output(BaseModel):
    product: int


class MathMultiply:
    """Multiply two numbers and return the product."""

    input_schema = Input
    output_schema = Output
    description = "Multiply two numbers and return the product"

    def execute(self, inputs, context=None):
        return {"product": inputs["a"] * inputs["b"]}
