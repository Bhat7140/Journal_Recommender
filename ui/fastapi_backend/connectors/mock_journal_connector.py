import copy
import json
from pathlib import Path

RECOMMENDATIONS_FILE = Path(__file__).resolve().parents[1] / "data" / "frontend_recommendations.json"


def load_recommendation_payload() -> dict:
    parsed = json.loads(RECOMMENDATIONS_FILE.read_text(encoding="utf-8"))
    return copy.deepcopy(parsed)
