import JournalCard from './JournalCard'

function Results({ filteredJournals, title, isLoading, error, onRetry }) {
  return (
    <section className="results">
      <div className="results-header">
        <h2>Recommended Journals</h2>
        <p>
          Matching against <strong>{title || 'your manuscript'}</strong>
        </p>
      </div>

      {isLoading && (
        <div className="status-panel">
          <p>Loading journals...</p>
        </div>
      )}

      {!isLoading && error && (
        <div className="status-panel status-error">
          <p>{error}</p>
          <button className="ghost-button" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !error && filteredJournals.length === 0 && (
        <div className="status-panel">
          <p>No journals matched the current search.</p>
        </div>
      )}

      {!isLoading && !error && filteredJournals.length > 0 && (
        <div className="cards">
          {filteredJournals.map((journal, index) => (
            <JournalCard
              key={journal.journal_name}
              journal={journal}
              index={index}
            />
          ))}
        </div>
      )}
    </section>
  )
}

export default Results
