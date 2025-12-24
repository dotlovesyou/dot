"""
Grok Image Generation for Dot the Ladybug

Uses xAI's Grok-2 image generation API to create images for tweets.
"""

import os
import sys
import httpx
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_API_URL = "https://api.x.ai/v1/images/generations"

# Image storage directory
IMAGE_DIR = Path(__file__).parent / "generated_images"
IMAGE_DIR.mkdir(exist_ok=True)


async def generate_image(prompt: str, save_path: str = None) -> dict:
    """
    Generate an image using Grok-2 image model.

    Args:
        prompt: Text description of the image to generate
        save_path: Optional path to save the image. If None, auto-generates filename.

    Returns:
        dict with 'success', 'image_path' or 'error'
    """
    if not XAI_API_KEY:
        return {
            "success": False,
            "error": "XAI_API_KEY not set. Get your API key from x.ai/api"
        }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                XAI_API_URL,
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-2-image",
                    "prompt": prompt,
                    "response_format": "b64_json",
                    "n": 1
                }
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API error {response.status_code}: {response.text}"
                }

            data = response.json()

            # Extract base64 image data
            if "data" in data and len(data["data"]) > 0:
                image_b64 = data["data"][0].get("b64_json")

                if image_b64:
                    # Decode and save image
                    image_bytes = base64.b64decode(image_b64)

                    if save_path is None:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        save_path = IMAGE_DIR / f"dot_image_{timestamp}.jpg"
                    else:
                        save_path = Path(save_path)

                    save_path.write_bytes(image_bytes)

                    return {
                        "success": True,
                        "image_path": str(save_path)
                    }

            return {
                "success": False,
                "error": "No image data in response"
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Request timed out - image generation can take up to 60 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def generate_dot_image(tweet_text: str = None) -> dict:
    """
    Generate a Dot-themed image for a tweet.

    Args:
        tweet_text: Optional tweet text to inspire the image

    Returns:
        dict with 'success', 'image_path' or 'error'
    """
    # Create a prompt that fits Dot's personality
    base_prompt = "A cute cartoon ladybug character named Dot"

    if tweet_text:
        # Create image prompt inspired by tweet content
        prompt = f"{base_prompt} in a whimsical scene inspired by: {tweet_text}. Kawaii style, cheerful, nature-themed, soft colors, dreamy atmosphere."
    else:
        # Default Dot image
        prompt = f"{base_prompt} exploring a magical garden with flowers and leaves. Kawaii style, cheerful, nature-themed, soft pastel colors, dreamy atmosphere."

    return await generate_image(prompt)


# For testing
if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing Grok image generation...")
        print()

        if not XAI_API_KEY:
            print("XAI_API_KEY not set!")
            print("Add your key to .env file:")
            print("XAI_API_KEY=your-key-here")
            return

        result = await generate_dot_image("Enjoying a sunny day in the garden!")

        if result["success"]:
            print(f"Image saved to: {result['image_path']}")
        else:
            print(f"Error: {result['error']}")

    asyncio.run(test())
