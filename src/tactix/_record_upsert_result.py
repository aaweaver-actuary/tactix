from tactix.base_db_store import PgnUpsertPlan


def _record_upsert_result(
    cur,
    key: tuple[str, str],
    plan: PgnUpsertPlan,
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> int:
    if not cur.rowcount:
        return 0
    latest_cache[key] = (plan.pgn_hash, plan.pgn_version)
    return 1
