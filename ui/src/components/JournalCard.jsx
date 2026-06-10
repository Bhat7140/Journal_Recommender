import { useState } from 'react'
import MatchRing from './MatchRing'

function JournalCard({ journal, index }) {
  const [showAllPapers, setShowAllPapers] = useState(false)
  const detailHref = `/#journal=${encodeURIComponent(journal.journal_name)}`
  const hiddenPaperCount = Math.max(0, journal.supporting_papers.length - 1)
  const visibleSupportingPapers = showAllPapers
    ? journal.supporting_papers
    : journal.supporting_papers.slice(0, 1)

  return (
    <article
      className="card"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="card-header">
        <h3>{journal.journal_name}</h3>
        <MatchRing score={journal.match_score_percent / 100} />
      </div>
      <p className="doi">ISSN: {journal.issn.join(', ')}</p>
      <div className="card-meta">
        <span className={`confidence-pill confidence-${journal.confidence}`}>
          {journal.confidence} confidence
        </span>
        <span className="rank-pill">Rank #{journal.rank}</span>
      </div>
      <div className="supporting-preview">
        <p className="supporting-title">Best supporting paper</p>
        {visibleSupportingPapers.map((paper) => (
          <div key={paper.title} className="supporting-paper-item">
            <strong>{paper.title}</strong>
            <span>Hybrid score: {paper.hybrid_score.toFixed(3)}</span>
          </div>
        ))}
        {!showAllPapers && hiddenPaperCount > 0 && (
          <button
            className="inline-button"
            type="button"
            onClick={() => setShowAllPapers(true)}
          >
            Show more supporting papers ({hiddenPaperCount})
          </button>
        )}
      </div>
      <div className="card-footer">
        <p>{journal.reason}</p>
        <a
          className="card-link"
          href={detailHref}
          target="_blank"
          rel="noreferrer"
        >
          View journal
        </a>
      </div>
    </article>
  )
}

export default JournalCard
