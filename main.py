import asyncio
from presentation.cli import ScraperCLI

async def _run():
    cli = ScraperCLI()
    await cli.run()

if __name__ == "__main__":
    asyncio.run(_run())
