def to_int(value: object) -> int | None:
    """Coerce a value to an integer if possible.

    Args:
        value: Value to coerce.

    Returns:
        Integer value or None.
    """

    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
