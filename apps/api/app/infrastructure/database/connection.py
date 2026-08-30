import psycopg

from app.core.config import settings


def check_database_connection() -> bool:
    try:
        with psycopg.connect(settings.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

        return result == (1,)

    except psycopg.Error as error:
        print(f"Database connection error: {error}")
        return False