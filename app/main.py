"""Index Tracker API: store securities and prices, and calculate a market-cap-weighted index."""

import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .index_calc import compute_index_levels

logger = logging.getLogger("index_tracker")

DbSession = Annotated[Session, Depends(get_db)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fine for a demo; a production service would use migrations (e.g. Alembic).
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Index Tracker API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/securities", response_model=schemas.SecurityOut, status_code=201)
def create_security(payload: schemas.SecurityCreate, db: DbSession):
    existing = db.scalar(select(models.Security).where(models.Security.ticker == payload.ticker))
    if existing:
        raise HTTPException(status_code=409, detail=f"{payload.ticker} already exists")
    security = models.Security(**payload.model_dump())
    db.add(security)
    db.commit()
    logger.info("created security %s", security.ticker)
    return security


@app.get("/securities", response_model=list[schemas.SecurityOut])
def list_securities(db: DbSession):
    return db.scalars(select(models.Security).order_by(models.Security.ticker)).all()


@app.post("/prices", response_model=schemas.UpsertResult)
def upsert_prices(payload: schemas.PriceBulk, db: DbSession):
    """Insert or update closing prices. All-or-nothing: unknown tickers reject the whole batch."""
    tickers = {p.ticker for p in payload.prices}
    securities = db.scalars(
        select(models.Security).where(models.Security.ticker.in_(tickers))
    ).all()
    by_ticker = {s.ticker: s for s in securities}

    unknown = sorted(tickers - set(by_ticker))
    if unknown:
        raise HTTPException(status_code=404, detail=f"unknown tickers: {unknown}")

    inserted = updated = 0
    for item in payload.prices:
        security = by_ticker[item.ticker]
        existing = db.scalar(
            select(models.Price).where(
                models.Price.security_id == security.id,
                models.Price.price_date == item.price_date,
            )
        )
        if existing:
            existing.close = item.close
            updated += 1
        else:
            db.add(
                models.Price(security_id=security.id, price_date=item.price_date, close=item.close)
            )
            inserted += 1
    db.commit()
    return schemas.UpsertResult(inserted=inserted, updated=updated)


@app.get("/index/levels", response_model=list[schemas.IndexLevel])
def index_levels(
    db: DbSession,
    start: Annotated[date | None, Query(description="First date to return")] = None,
    end: Annotated[date | None, Query(description="Last date to return")] = None,
):
    """Index levels for all stored securities. The base level (1000) is the first stored date."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must not be after end")

    securities = db.scalars(select(models.Security)).all()
    if not securities:
        raise HTTPException(status_code=409, detail="no securities have been added yet")
    shares = {s.ticker: s.shares_outstanding for s in securities}

    rows = db.execute(
        select(models.Price.price_date, models.Security.ticker, models.Price.close)
        .select_from(models.Price)
        .join(models.Security)
    ).all()
    prices_by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for price_date, ticker, close in rows:
        prices_by_date[price_date][ticker] = close

    try:
        levels = compute_index_levels(prices_by_date, shares)
    except ValueError as exc:
        logger.warning("index calculation rejected: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return [
        schemas.IndexLevel(as_of=day, level=level, daily_return=daily_return)
        for day, level, daily_return in levels
        if (start is None or day >= start) and (end is None or day <= end)
    ]
