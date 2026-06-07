FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# GEE credentials: mount at runtime with
#   -v ~/.config/earthengine:/root/.config/earthengine:ro
# Output data: mount at runtime with
#   -v $(pwd)/data_collected:/app/data_collected

CMD ["uv", "run", "python", "landsat_data_collection.py"]
