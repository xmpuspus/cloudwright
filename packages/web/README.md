# cloudwright-web

Web UI for [Cloudwright](https://github.com/xmpuspus/cloudwright) architecture and migration intelligence. FastAPI backend with React frontend.

## Install

```bash
pip install 'cloudwright-ai[web]'
```

## Usage

```bash
cloudwright chat --web
```

The browser opens at `http://localhost:8765`. The workspace covers design, cost, validation,
compliance, deploy checks, migration planning, evidence checks, review, export, and spec editing.

The Migration tab runs a packaged PH telco proof project through the industry-neutral planner. It
shows ordered waves, supplied costs, and closure evidence. The API exposes
`/api/migration/packs`, `/api/migration/plan`, `/api/migration/verify`, and `/api/migration/demo`.

See the [main project README](https://github.com/xmpuspus/cloudwright) for full documentation.
