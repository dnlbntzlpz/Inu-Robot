import asyncio
import sys
import signal
import logging
from asyncio import create_subprocess_exec
from typing import Optional
from pyngrok import ngrok
from pyngrok.exception import PyngrokError

logging.getLogger("pyngrok").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.ERROR)


class AppRunner:
    def __init__(self, port: int = 5001, app_path: str = "app.py", startup_timeout: int = 10):
        self.port = port
        self.app_path = app_path
        self.startup_timeout = startup_timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self.public_url = None
        signal.signal(signal.SIGINT, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        print("\nShutting down server...")
        print("="*70)
        if self.public_url:
            try:
                ngrok.disconnect(self.public_url)
            except:
                pass
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
        sys.exit(0)

    async def start_app(self) -> None:
        try:
            self.process = await create_subprocess_exec(
                sys.executable, self.app_path,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await asyncio.sleep(self.startup_timeout)
        except Exception as e:
            print(f"\n❌ Failed to start Flask app: {e}")
            raise

    async def start_ngrok(self) -> None:
        try:
            tunnel = ngrok.connect(self.port)
            self.public_url = str(tunnel)
            url = str(tunnel).split('"')[1]
            print("="*70)
            print(f"\n🌐 Your server is running at: \033[1;32m{url}\033[0m")
            print("="*70 + "\n")
        except PyngrokError as e:
            print(f"\n❌ ngrok tunnel failed: {e}")
            raise

    async def run(self) -> None:
        print("\nStarting server...")
        await self.start_app()
        await self.start_ngrok()
        try:
            await self.process.wait()
        except asyncio.CancelledError:
            pass


def main():
    runner = AppRunner()
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
