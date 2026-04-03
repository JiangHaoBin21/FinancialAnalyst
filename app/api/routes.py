"""API route definitions."""


def register_routes() -> list[str]:
    """Return the route names exposed by the API layer."""
    return ["health_check", "analysis"]
