from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import RecommendationSearchResponse
from .services.journal_service import get_journal_by_id, get_journals

app = FastAPI(title="Journal Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/journals", response_model=RecommendationSearchResponse)
def list_journals(
    title: str = "",
    abstractText: str = "",
    references: str = "",
    domain: str = "all",
    openAccessOnly: bool = False,
    keyword: str = "",
    sortBy: str = Query(default="match"),
):
    try:
        return get_journals(
            title=title,
            abstract_text=abstractText,
            references=references,
            domain=domain,
            open_access_only=openAccessOnly,
            keyword=keyword,
            sort_by=sortBy,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/journals/{journal_id}")
def journal_detail(journal_id: str):
    journal = get_journal_by_id(journal_id)
    if journal is None:
        raise HTTPException(status_code=404, detail=f"Journal {journal_id} not found")
    return journal
