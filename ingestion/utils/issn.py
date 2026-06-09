def normalize_issn(issn):
    if not issn:
        return None

    value = str(issn).strip().upper().replace("-", "")
    if len(value) != 8:
        return None

    return f"{value[:4]}-{value[4:]}"


def normalize_issn_list(values):
    if not values:
        return []
    if not isinstance(values, list):
        values = [values]

    normalized = []
    seen = set()
    for value in values:
        issn = normalize_issn(value)
        if issn and issn not in seen:
            normalized.append(issn)
            seen.add(issn)

    return normalized


def has_issn(record):
    if hasattr(record, "issn"):
        return bool(normalize_issn_list(record.issn))
    return bool(normalize_issn_list(record.get("issn")))
