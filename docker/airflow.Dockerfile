FROM apache/airflow:2.10.0-python3.12

ENV PYTHONPATH=/opt/tactix/src

USER root

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		curl \
		git \
		pkg-config \
		stockfish \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /opt/tactix

COPY pyproject.toml Cargo.toml README.md /opt/tactix/
COPY src /opt/tactix/src
COPY airflow/dags /opt/airflow/dags

RUN chown -R airflow: /opt/airflow /opt/tactix

USER airflow

RUN pip install --no-cache-dir \
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
