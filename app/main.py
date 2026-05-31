"""
Web Page to Markdown API — FastAPI application.

Provides a single endpoint /convert that accepts a URL and returns
clean markdown extracted from the page content.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from app.converters import (
    url_to_markdown,
    ConversionError,
    InvalidURLError,
    TimeoutError,
    ResponseTooLargeError,
    FetchError,
    ExtractionError,
)

app = FastAPI(
    title="Web Page to Markdown API",
    version="1.0.0",
    description=(
        "Convert any web page to clean, readable Markdown. "
        "Extracts article content using Mozilla's Readability algorithm, "
        "strips navigation, ads, and sidebars."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Response models ────────────────────────────────────────────────────────


class ConvertResponse(BaseModel):
    title: str | None = None
    markdown: str
    source_url: str
    length: int


class ErrorResponse(BaseModel):
    error: str
    detail: str


# ── Health ─────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "title": "Web Page to Markdown API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "convert": "GET /convert?url=<url>",
        },
    }


# ── Convert endpoint ───────────────────────────────────────────────────────


@app.get(
    "/convert",
    response_model=ConvertResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def convert(
    url: str = Query(
        ...,
        description="The URL of the web page to convert to Markdown.",
        min_length=1,
        max_length=2000,
    ),
):
    """
    Convert a web page to clean Markdown.

    The API fetches the page, extracts the article content using Mozilla's
    Readability algorithm, and converts it to clean Markdown.
    """
    try:
        result = await url_to_markdown(url)
        return ConvertResponse(**result)
    except InvalidURLError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))
    except ResponseTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ConversionError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
