import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
import redis

from database import Base, engine, get_db
from models import URL
from schemas import URLCreate, URLCreated

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def wait_for_db(max_retries: int = 20, delay_seconds: float = 1.0) -> None:
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(delay_seconds)


wait_for_db()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")

ALPHABET = (
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
)


def encode_base62(number: int) -> str:
    if number == 0:
        return ALPHABET[0]

    result = []
    while number:
        number, remainder = divmod(number, 62)
        result.append(ALPHABET[remainder])

    return "".join(reversed(result))


@app.post("/api/v1/urls", response_model=URLCreated)
def create_url(
    payload: URLCreate,
    db: Session = Depends(get_db),
):
    url = URL(
        original_url=str(payload.original_url),
        short_code="pending",
    )
    db.add(url)
    db.flush()  # Obtain the database-generated ID.

    url.short_code = encode_base62(url.id)
    db.commit()
    db.refresh(url)

    return URLCreated(
        short_code=url.short_code,
        short_url=f"http://localhost:8000/{url.short_code}",
        original_url=url.original_url,
    )


@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    cache_key = f"url:{short_code}"

    # 1. Try Redis first.
    cached_url = redis_client.get(cache_key)

    if cached_url is not None:
        return RedirectResponse(
            url=cached_url,
            status_code=302,
        )
    
    statement = select(URL).where(URL.short_code == short_code)
    url = db.scalar(statement)

    if url is None:
        raise HTTPException(status_code=404, detail="URL not found")

     # 3. Populate Redis for five minutes.
    redis_client.set(
        cache_key,
        url.original_url,
        ex=300,
    )

     # 4. Redirect the client.
    return RedirectResponse(
        url=url.original_url,
        status_code=302,
    )