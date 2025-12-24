"""
Tweet with Image - Helper for posting tweets with images.
Uses twitter_browser.py infrastructure.
"""

import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent / "twitter_cookies.json"


async def tweet_with_image(text: str, image_path: str) -> dict:
    """Post a tweet with an image using browser automation."""

    if not COOKIES_FILE.exists():
        return {"success": False, "error": "No cookies found. Run: python twitter_browser.py setup"}
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image not found: {image_path}"}

    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        try:
            brave_path = os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe")
            if not os.path.exists(brave_path):
                brave_path = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
            launch_args = {"headless": True}
            if os.path.exists(brave_path):
                launch_args["executable_path"] = brave_path

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            await context.add_cookies(cookies)
            page = await context.new_page()

            await page.goto("https://x.com/home", timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            if "login" in page.url.lower():
                await context.close()
                await browser.close()
                return {"success": False, "error": "Not logged in. Cookies may have expired."}

            await asyncio.sleep(3)

            # Find compose box
            selectors = ['[data-testid="tweetTextarea_0"]', '[aria-label="Post text"]', '[role="textbox"]']
            compose_box = None
            for selector in selectors:
                try:
                    compose_box = await page.wait_for_selector(selector, timeout=10000)
                    if compose_box:
                        break
                except:
                    continue

            if not compose_box:
                await context.close()
                await browser.close()
                return {"success": False, "error": "Could not find tweet compose box."}

            await compose_box.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type(text, delay=50)
            await asyncio.sleep(1)

            # Find file input for image upload
            file_input = await page.query_selector('input[type="file"][accept*="image"]')
            if not file_input:
                file_input = await page.query_selector('input[data-testid="fileInput"]')
            if not file_input:
                await context.close()
                await browser.close()
                return {"success": False, "error": "Could not find image upload input."}

            # Upload the image
            await file_input.set_input_files(image_path)
            await asyncio.sleep(3)  # Wait for upload

            # Find Post button
            post_selectors = ['[data-testid="tweetButtonInline"]', '[data-testid="tweetButton"]', 'button:has-text("Post")']
            post_button = None
            for selector in post_selectors:
                try:
                    post_button = await page.wait_for_selector(selector, timeout=3000)
                    if post_button:
                        break
                except:
                    continue

            if not post_button:
                await context.close()
                await browser.close()
                return {"success": False, "error": "Could not find Post button."}

            await post_button.click()
            await asyncio.sleep(3)
            await context.close()
            await browser.close()

            return {"success": True, "tweet": text, "image": image_path, "method": "browser_automation"}

        except Exception as e:
            try:
                await browser.close()
            except:
                pass
            return {"success": False, "error": str(e)}


# For testing
if __name__ == "__main__":
    import sys

    async def test():
        if len(sys.argv) < 3:
            print("Usage: python tweet_image.py <image_path> <tweet text>")
            return

        image_path = sys.argv[1]
        text = " ".join(sys.argv[2:])

        print(f"Tweeting with image: {image_path}")
        print(f"Text: {text}")

        result = await tweet_with_image(text, image_path)

        if result["success"]:
            print("Tweet posted successfully!")
        else:
            print(f"Error: {result['error']}")

    asyncio.run(test())
