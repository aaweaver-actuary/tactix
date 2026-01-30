from uuid import uuid4


def generate_id() -> str:
    """Generate a unique identifier string.

    Returns:
        A unique identifier as a string.
    """
    return str(uuid4())
