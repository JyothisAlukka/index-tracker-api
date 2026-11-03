"""Pydantic request/response schemas with input validation."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SecurityCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=128)
    shares_outstanding: int = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalise_ticker(cls, value: str) -> str:
        return value.strip().upper()


class SecurityOut(SecurityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PriceIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    price_date: date
    close: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalise_ticker(cls, value: str) -> str:
        return value.strip().upper()


class PriceBulk(BaseModel):
    prices: list[PriceIn] = Field(min_length=1)


class UpsertResult(BaseModel):
    inserted: int
    updated: int


class IndexLevel(BaseModel):
    as_of: date
    level: float
    daily_return: float | None
