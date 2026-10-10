from pydantic import BaseModel, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLCreated(BaseModel):
    short_code: str
    short_url: str
    original_url: str