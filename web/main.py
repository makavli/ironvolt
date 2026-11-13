"""The browser entry point: pygbag packs this folder (see tools/web_build.sh) and runs it in the page."""
import asyncio
import sys
import traceback

import pygame  # noqa: F401  pygbag fetches the packages it sees imported here, so pygame must be named in this file

from ironvolt.app import App


async def main():
    try:
        await App().run_web()
    except Exception:
        if sys.platform == "emscripten":         # the page's console, where tools/web_check.py reads it
            import platform
            platform.window.console.error(traceback.format_exc())
        raise


asyncio.run(main())
