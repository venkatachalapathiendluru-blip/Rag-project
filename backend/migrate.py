"""Apply database migrations: python -m backend.migrate"""

from backend.db import close_pool, connection, migrate


def main():
    with connection() as conn:
        applied = migrate(conn)

    close_pool()
    print("Applied:", applied or "nothing to do")


if __name__ == "__main__":
    main()
