from enum import StrEnum
from typing import Self
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

class State(StrEnum):
    draft = "draft"
    active = "active"

class Supplier(BaseModel):
    name: str = Field(min_length=1)
    city: str

class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)
    sale_price_minor: int | None = Field(default=None, ge=0, strict=True)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    stock_by_city: dict[str, int] = Field(default_factory=dict)
    supplier: Supplier
    state: State = State.draft

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value

    @model_validator(mode="after")
    def valid_sale(self) -> Self:
        if self.sale_price_minor is not None and self.sale_price_minor > self.price_minor:
            raise ValueError("Sale price cannot exceed regular price")
        return self

if __name__ == "__main__":
    product = ProductCreate.model_validate({"name": " Pen ", "price_minor": 2000, "supplier": {"name": "PaperCo", "city": "Pune"}})
    print(product.model_dump(mode="json"))
    print(product.model_dump_json())
    try:
        ProductCreate.model_validate({"name": "Pen", "price_minor": "2000", "supplier": {"name": "PaperCo"}})
    except ValidationError as error:
        print(error.errors())
