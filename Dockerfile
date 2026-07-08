FROM python:3.12-slim

WORKDIR /app

COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/core/cloudwright/ packages/core/cloudwright/
COPY packages/web/pyproject.toml packages/web/pyproject.toml
COPY packages/web/cloudwright_web/ packages/web/cloudwright_web/

RUN pip install --no-cache-dir ./packages/core ./packages/web

# This CMD binds 0.0.0.0 directly via uvicorn, bypassing the CLI's serve()
# (the only place that used to enforce CLOUDWRIGHT_API_KEY). Setting this
# makes cloudwright_web.app.create_app() refuse to start unauthenticated.
ENV CLOUDWRIGHT_REQUIRE_AUTH=1

EXPOSE 8000

CMD ["uvicorn", "cloudwright_web.app:app", "--host", "0.0.0.0", "--port", "8000"]
