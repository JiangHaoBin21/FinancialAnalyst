"""Seed company records for local development."""

from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.company_repo import CompanyRepository


def main() -> None:
    """Run the company seed placeholder."""
    repository = CompanyRepository()
    print(repository.get())


if __name__ == "__main__":
    main()
