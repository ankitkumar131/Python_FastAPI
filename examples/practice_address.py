from pydantic import BaseModel, ConfigDict, Field, field_validator
class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")
    city: str
    postal_code: str = Field(pattern=r"^[0-9]{6}$")
    @field_validator("city")
    @classmethod
    def clean_city(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("City cannot be blank")
        return value
print(Address(city=" Pune ", postal_code="411001").model_dump())
