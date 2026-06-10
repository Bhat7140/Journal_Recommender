async function readJson(response) {
  const payload = await response.json()

  if (!response.ok) {
    throw new Error(payload.error || payload.detail || 'Request failed')
  }

  return payload
}

export async function fetchJournals(params) {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value === '' || value === null || value === undefined) return
    searchParams.set(key, String(value))
  })

  const response = await fetch(`/api/journals?${searchParams.toString()}`)
  return readJson(response)
}

export async function fetchJournalById(id) {
  const response = await fetch(`/api/journals/${encodeURIComponent(id)}`)
  return readJson(response)
}
