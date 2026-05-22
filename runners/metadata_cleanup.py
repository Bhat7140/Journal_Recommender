from concurrent.futures import ThreadPoolExecutor, as_completed

from data_sources.journal_lookup import JournalNameResolver
from utils.issn import normalize_issn_list


def require_issn_and_journal_names(records, max_workers=12):
    resolver = JournalNameResolver()
    candidates = []

    for record in records:
        record.issn = normalize_issn_list(record.issn)
        if not record.issn:
            continue
        candidates.append(record)

    missing_issn_values = sorted(
        {
            issn
            for record in candidates
            if not record.journal_name
            for issn in record.issn
        }
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(resolver.resolve, [issn]): issn
            for issn in missing_issn_values
        }
        resolved_names = {}

        for future in as_completed(futures):
            issn = futures[future]
            try:
                resolved_names[issn] = future.result()
            except Exception as e:
                print(f"Failed journal lookup for {issn}: {e}")

    for record in candidates:
        if record.journal_name:
            continue

        for issn in record.issn:
            if resolved_names.get(issn):
                record.journal_name = resolved_names[issn]
                break

    return candidates
