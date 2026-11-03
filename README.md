# Index Tracker API

A small REST service that stores securities and their daily closing prices and calculates a
**market-cap-weighted index** from them. Built with Python, FastAPI, SQLAlchemy and PostgreSQL,
with automated tests, Docker and a CI pipeline.

## How the index works

The index starts at a base level of 1000 on the first date with data. Every later level
is scaled by the change in total market capitalisation:

```
level_t = 1000 * sum(price_t * shares) / sum(price_base * shares)
```

Larger companies therefore move the index more. The calculation lives in `app/index_calc.py` as a
pure function with no database or web dependencies, so it is simple to test.

## Endpoints

| Method | Path             | Purpose                                              |
|--------|------------------|------------------------------------------------------|
| GET    | `/health`        | Liveness check                                       |
| POST   | `/securities`    | Add a security (ticker, name, shares outstanding)    |
| GET    | `/securities`    | List securities                                      |
| POST   | `/prices`        | Insert or update closing prices in bulk (upsert)     |
| GET    | `/index/levels`  | Index level and daily return per date (`start`, `end` filters) |

Interactive docs are served at `/docs`.

## Run it

With Docker (PostgreSQL included):

```bash
docker compose up --build
```

Locally with SQLite (no database setup):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Example:

```bash
curl -X POST localhost:8000/securities -H 'content-type: application/json' \
  -d '{"ticker":"AAA","name":"Alpha Corp","shares_outstanding":100}'
curl -X POST localhost:8000/prices -H 'content-type: application/json' \
  -d '{"prices":[{"ticker":"AAA","price_date":"2026-01-01","close":10.0}]}'
curl localhost:8000/index/levels
```

## Tests and quality checks

```bash
pytest -v
ruff check .
```

Tests use an in-memory SQLite database, so they need no running PostgreSQL. GitHub Actions runs
linting, tests and a Docker build on every push and pull request.

## Design decisions

- **Incomplete data is rejected, not guessed.** If any constituent has no price on a date, the
  index endpoint returns a 422 with the missing tickers rather than producing a wrong number.
- **Price upserts are all-or-nothing.** An unknown ticker rejects the whole batch.
- **Unique constraint** on (security, date) enforces one closing price per day in the database.
- **Date filters keep the original base.** Filtering with `start` returns a slice of the same
  series; it does not rebase the index.

## Known limitations and next steps

- Prices use floating point for simplicity. A production index would use `Decimal`/`NUMERIC`.
- Tables are created at startup. A real service would use Alembic migrations.
- Constituents and share counts are fixed over time; real indices handle corporate actions,
  rebalancing and free-float adjustments.
- No authentication or pagination.
