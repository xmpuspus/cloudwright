# cloudwright-web

Web UI for Cloudwright. FastAPI backend wrapping core package + React frontend.

## Backend

`backend/app.py` — FastAPI app with endpoints for design, cost, validate, export, catalog.

## Frontend

React + TypeScript + Vite. Interactive architecture diagrams with React Flow,
cost tables, comparison views. Same chat experience as the CLI but visual.

## Running

```bash
cloudwright serve          # starts both backend and frontend
cloudwright chat --web     # same thing
```
