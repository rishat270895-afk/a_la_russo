from dotenv import load_dotenv

load_dotenv()

from app.bot import main  # noqa: E402


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
