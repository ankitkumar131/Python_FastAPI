from pydantic import BaseModel, ConfigDict, Field

class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    price_minor: int = Field(ge=0, strict=True)

class ProductRead(ProductWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
