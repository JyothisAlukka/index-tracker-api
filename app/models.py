"""ORM models: securities (index constituents) and their daily closing prices."""

from datetime import date

from sqlalchemy import BigInteger, Date, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Security(Base):
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    shares_outstanding: Mapped[int] = mapped_column(BigInteger)

    prices: Mapped[list["Price"]] = relationship(
        back_populates="security", cascade="all, delete-orphan"
    )


class Price(Base):
    __tablename__ = "prices"
    # One closing price per security per day.
    __table_args__ = (UniqueConstraint("security_id", "price_date", name="uq_security_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    security_id: Mapped[int] = mapped_column(ForeignKey("securities.id"), index=True)
    price_date: Mapped[date] = mapped_column(Date, index=True)
    close: Mapped[float] = mapped_column(Float)

    security: Mapped[Security] = relationship(back_populates="prices")
