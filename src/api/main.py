from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.models import SearchRequest, SearchResponse, BookMetadata
from scrapers.example_library_scraper import ExampleLibraryScraper
from scrapers.noworzyn_scraper import NoworzynScraper
import asyncio
from typing import Dict, Type
from scrapers.base_scraper import BaseScraper

app = FastAPI(
    title="Bibliotheksübergreifendes Suchsystem",
    description="API für die parallele Suche in mehreren Bibliothekskatalogen",
    version="1.0.0"
)

# CORS-Middleware für Frontend-Zugriff
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registry für verfügbare Bibliotheks-Scraper
LIBRARY_SCRAPERS: Dict[str, Type[BaseScraper]] = {
    "example_library": ExampleLibraryScraper,
    "noworzyn": NoworzynScraper,
}

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Führt eine parallele Suche in den ausgewählten Bibliotheken durch.
    """
    results = []
    errors = []
    tasks = []

    # Erstelle Scraper-Instanzen für ausgewählte Bibliotheken
    for library in request.libraries:
        if library not in LIBRARY_SCRAPERS:
            errors.append(f"Bibliothek '{library}' nicht unterstützt")
            continue
        
        scraper = LIBRARY_SCRAPERS[library]()
        tasks.append(scraper.search(request.query, **(request.filters or {})))

    # Führe Suchen parallel aus
    if tasks:
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verarbeite Ergebnisse und Fehler
        for library, result in zip(request.libraries, search_results):
            if isinstance(result, Exception):
                errors.append(f"Fehler bei '{library}': {str(result)}")
            else:
                for item in result:
                    results.append(BookMetadata(
                        **item,
                        library=library
                    ))

    return SearchResponse(
        results=results,
        total_count=len(results),
        errors=errors if errors else None
    )

@app.get("/libraries")
async def get_available_libraries():
    """
    Gibt eine Liste der verfügbaren Bibliotheken zurück.
    """
    return {"libraries": list(LIBRARY_SCRAPERS.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 