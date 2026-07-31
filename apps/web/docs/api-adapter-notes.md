# API Adapter Notes

The frontend remains in mock mode by default. Existing pages continue to use mock repositories and localStorage behavior.

## Modes

- `NEXT_PUBLIC_DATA_SOURCE_MODE=mock`: use local mock repositories.
- `NEXT_PUBLIC_DATA_SOURCE_MODE=api`: call the FastAPI skeleton through the adapter layer.

The default is mock mode, and no environment variable is required to run the app.

## Backend Requirement For API Mode

API mode expects the backend to run at:

```txt
http://localhost:8000
```

Override with:

```txt
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Why Adapters

UI pages should eventually call adapter functions instead of direct repositories. This lets us switch from mock/localStorage data to FastAPI responses without rewriting the screens.

Current adapter groups:

- platform adapter
- company adapter
- learner adapter
- session adapter
- usage adapter

Phase 2D does not fully migrate the UI to API mode. It only prepares the boundary.
