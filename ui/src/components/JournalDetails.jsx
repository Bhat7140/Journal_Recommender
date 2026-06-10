function DetailRow({ label, value }) {
  return (
    <div className="detail-row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function JournalDetails({ journal, isLoading = false, error = '', onRetry }) {
  if (isLoading) {
    return (
      <section className="journal-detail panel detail-empty">
        <h3>Loading journal</h3>
        <p>Fetching journal details from the API.</p>
      </section>
    )
  }

  if (error) {
    return (
      <section className="journal-detail panel detail-empty">
        <h3>Unable to load journal</h3>
        <p>{error}</p>
        <button className="ghost-button" type="button" onClick={onRetry}>
          Retry
        </button>
      </section>
    )
  }

  if (!journal) {
    return (
      <section className="journal-detail panel detail-empty">
        <h3>Select a journal</h3>
        <p>Choose a result card to inspect match reasoning and supporting papers.</p>
      </section>
    )
  }

  return (
    <section className="journal-detail panel">
      <div className="detail-title-row">
        <div>
          <p className="detail-eyebrow">Recommended journal</p>
          <h2>{journal.journal_name}</h2>
          <p className="detail-description">{journal.reason}</p>
        </div>
      </div>

      <div className="detail-layout">
        <dl className="detail-grid">
          <DetailRow label="Rank:" value={journal.rank} />
          <DetailRow label="Match score:" value={`${journal.match_score_percent}%`} />
          <DetailRow label="Confidence:" value={journal.confidence} />
          <DetailRow label="ISSNs:" value={journal.issn.join(', ')} />
          <DetailRow label="Supporting paper count:" value={journal.supporting_paper_count} />
          <DetailRow label="Best matching paper:" value={journal.best_matching_paper.title} />
          <DetailRow label="Best paper year:" value={journal.best_matching_paper.year} />
          <DetailRow label="Best paper DOI:" value={journal.best_matching_paper.doi} />
          <DetailRow
            label="Best paper hybrid score:"
            value={journal.best_matching_paper.hybrid_score.toFixed(3)}
          />
        </dl>

        <div className="detail-side">
          <div className="detail-links">
            <a
              className="detail-link"
              href={`https://doi.org/${journal.best_matching_paper.doi}`}
              target="_blank"
              rel="noreferrer"
            >
              Open best matching paper
            </a>
          </div>

          <div className="token-block">
            <h3>Supporting papers:</h3>
            <div className="token-list">
              {journal.supporting_papers.map((paper) => (
                <div key={paper.title} className="supporting-paper-card">
                  <strong>{paper.title}</strong>
                  <span>Hybrid score: {paper.hybrid_score.toFixed(3)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default JournalDetails
