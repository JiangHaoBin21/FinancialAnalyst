"""Application entrypoint for the FinancialAnalyst project."""


def create_app() -> dict[str, str]:
    """Return a minimal app descriptor until the web framework is wired in."""
    return {"name": "FinancialAnalyst", "status": "initialized"}


if __name__ == "__main__":
    app = create_app()
    print(f"{app['name']} is {app['status']}.")
