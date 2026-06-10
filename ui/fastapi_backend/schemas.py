from pydantic import BaseModel


class QueryPayload(BaseModel):
    title: str
    abstract: str


class MatchingPaper(BaseModel):
    title: str
    hybrid_score: float


class BestMatchingPaper(MatchingPaper):
    year: int
    doi: str


class RecommendationPayload(BaseModel):
    journal_name: str
    issn: list[str]
    match_score_percent: int
    confidence: str
    reason: str
    supporting_paper_count: int
    best_matching_paper: BestMatchingPaper
    supporting_papers: list[MatchingPaper]
    rank: int


class RecommendationSearchResponse(BaseModel):
    query: QueryPayload
    recommendations: list[RecommendationPayload]
