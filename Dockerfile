FROM node:22-bookworm-slim AS node
FROM python:3.12-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY vendor/korea-stock-mcp/package*.json vendor/korea-stock-mcp/
RUN cd vendor/korea-stock-mcp && npm install --omit=dev --ignore-scripts
COPY app app
COPY frontend frontend
COPY vendor/korea-stock-mcp/dist vendor/korea-stock-mcp/dist
COPY vendor/korean-news-mcp vendor/korean-news-mcp
COPY .streamlit .streamlit
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
