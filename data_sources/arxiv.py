import xml.etree.ElementTree as ET

from data_sources.base import BaseSource
from models.work import Work
from utils.http import normalize_doi, safe_get_text

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def text_or_none(element):
    if element is None or element.text is None:
        return None
    return " ".join(element.text.split())


def parse_year(value):
    if not value:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def parse_entries(xml_text):
    if not xml_text:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    return root.findall(f"{ATOM_NS}entry")


class ArxivSource(BaseSource):

    def search(self, query, limit=100):
        params = {
            "search_query": query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
        }
        xml_text = safe_get_text(ARXIV_API_URL, params)
        return parse_entries(xml_text)

    def get_by_doi(self, doi):
        normalized = normalize_doi(doi)
        if not normalized:
            return None

        results = self.search(f'doi:"{normalized}"', limit=1)
        return results[0] if results else None

    def normalize(self, item):
        title = text_or_none(item.find(f"{ATOM_NS}title"))
        abstract = text_or_none(item.find(f"{ATOM_NS}summary"))
        published = text_or_none(item.find(f"{ATOM_NS}published"))
        journal_ref = text_or_none(item.find(f"{ARXIV_NS}journal_ref"))
        doi = normalize_doi(text_or_none(item.find(f"{ARXIV_NS}doi")))

        authors = []
        for author in item.findall(f"{ATOM_NS}author"):
            name = text_or_none(author.find(f"{ATOM_NS}name"))
            if name:
                authors.append(name)

        subjects = []
        for category in item.findall(f"{ATOM_NS}category"):
            term = category.attrib.get("term")
            if term:
                subjects.append(term)

        return Work(
            doi=doi,
            title=title,
            abstract=abstract,
            year=parse_year(published),
            authors=authors,
            venue=journal_ref or "arXiv",
            subjects=subjects,
            issn=[],
            source={"arxiv": True},
        )
