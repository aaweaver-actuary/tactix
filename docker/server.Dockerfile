FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=1 \
	PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		curl \
		git \
		pkg-config \
		stockfish \
	&& rm -rf /var/lib/apt/lists/*

COPY pyproject.toml Cargo.toml README.md /app/
COPY src /app/src

RUN pip install --upgrade pip \
	&& pip install --no-cache-dir \
		"berserk>=0.13.0" \
		"duckdb>=1.4.3" \
		"fastapi>=0.115.0" \
		"orjson>=3.10.7" \
		"pandas>=2.2.3" \
		"pydantic>=2.9.0" \
		"python-chess>=1.999" \
		"python-dotenv>=1.2.1" \
		"requests>=2.32.3" \
		"tenacity>=9.0.0" \
		"uvicorn>=0.31.0"

EXPOSE 8000

CMD ["uvicorn", "tactix.api:app", "--host", "0.0.0.0", "--port", "8000"]
