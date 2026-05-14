from dataclasses import dataclass
from typing import List, Optional, Dict

@dataclass
class Work:
    doi: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    year: Optional[int]
    authors: List[str]
    venue: Optional[str]
    subjects: List[str] #MSC
    issn: List[str]
    source: Dict[str, bool]