function ManuscriptForm({
  title,
  setTitle,
  abstractText,
  setAbstractText,
  references,
  setReferences,
  filteredJournals,
  resultsTotal,
  isLoading,
  onSubmitSearch,
  onClear,
}) {
  return (
    <section className="panel hero">
      <div className="panel-header">
        <div>
          <h1>Manuscript-Based Search</h1>
          <p>
            Paste your manuscript details below for AI-powered journal
            recommendations.
          </p>
        </div>
        <div className="panel-metrics">
          <div>
            <span className="metric-label">Results</span>
            <strong>{isLoading ? '...' : resultsTotal}</strong>
          </div>
          <div>
            <span className="metric-label">High Confidence</span>
            <strong>
              {isLoading
                ? '...'
                : filteredJournals.filter((journal) => journal.confidence === 'high').length}
            </strong>
          </div>
        </div>
      </div>

      <form
        className="form-grid"
        onSubmit={(event) => {
          event.preventDefault()
          onSubmitSearch()
        }}
      >
        <label className="field">
          <span>Title</span>
          <input
            className="text-input dark"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Abstract</span>
          <textarea
            className="text-input dark"
            placeholder="Paste your abstract here..."
            value={abstractText}
            onChange={(event) => setAbstractText(event.target.value)}
          />
        </label>
        <label className="field">
          <span>References (Optional)</span>
          <textarea
            className="text-input dark"
            placeholder="Paste references, one per line..."
            value={references}
            onChange={(event) => setReferences(event.target.value)}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={isLoading}>
            Find Journals
          </button>
          <button className="ghost-button" type="button" onClick={onClear} disabled={isLoading}>
            Clear form
          </button>
        </div>
      </form>
    </section>
  )
}

export default ManuscriptForm
