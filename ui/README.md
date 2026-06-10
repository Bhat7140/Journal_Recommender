# Journal Recommender UI

React/Vite frontend with a small FastAPI backend.

The backend does not recollect metadata. It uses the stored embedding folders in
`output/embeddings/msc_clean` and `output/embeddings/physics_clean`, ensures the
matching OpenSearch index exists, embeds the submitted title/abstract, and runs
hybrid search.

## Run

Start the API:

```powershell
npm run dev:api
```

Start the frontend in another terminal:

```powershell
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

The API expects OpenSearch at `localhost:9200`.
