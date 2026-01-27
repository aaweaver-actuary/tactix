from pathlib import Path


EXPECTED_CONN = "postgresql+psycopg2://tactix:tactix@postgres:5432/tactix"


def assert_airflow_services_use_postgres(compose_path: Path) -> None:
    content = compose_path.read_text()
    assert EXPECTED_CONN in content, "Airflow metadata DB should use Postgres"
    for service in ("airflow-init:", "airflow-webserver:", "airflow-scheduler:"):
        assert service in content, f"Missing service definition: {service}"
    assert content.count(EXPECTED_CONN) >= 3, "All Airflow services should use Postgres"


def test_root_compose_uses_postgres_for_airflow() -> None:
    assert_airflow_services_use_postgres(Path("compose.yml"))


def test_docker_compose_uses_postgres_for_airflow() -> None:
    assert_airflow_services_use_postgres(Path("docker/compose.yml"))
