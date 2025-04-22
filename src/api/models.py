from pydantic import BaseModel
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str
    libraries: List[str]
    filters: Optional[dict] = None

class BookMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[str] = None
    isbn: Optional[str] = None
    availability: Optional[str] = None
    location: Optional[str] = None
    library: str

class SearchResponse(BaseModel):
    results: List[BookMetadata]
    total_count: int
    errors: Optional[List[str]] = None 