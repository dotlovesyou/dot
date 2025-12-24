"""
Twitter Browser Automation for Dot
Uses Playwright to tweet through the browser when logged in.

WARNING: This is against Twitter's ToS. Use at your own risk.
"""

import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

# Path to store browser session
SESSION_DIR = Path(__file__).parent / "browser_session"
COOKIES_FILE = Path(__file__).parent / "twitter_cookies.json"


def get_encryption_key():
    """Get the AES encryption key from Brave's Local State."""
    import os
    import base64

    local_state_path = os.path.expandvars(
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Local State"
    )

    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)

    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
    # Remove 'DPAPI' prefix
    encrypted_key = encrypted_key[5:]

    # Decrypt using Windows DPAPI
    import ctypes
    import ctypes.wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ('cbData', ctypes.wintypes.DWORD),
            ('pbData', ctypes.POINTER(ctypes.c_char))
        ]

    def decrypt_dpapi(encrypted):
        blob_in = DATA_BLOB(len(encrypted), ctypes.create_string_buffer(encrypted, len(encrypted)))
        blob_out = DATA_BLOB()

        if ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
        ):
            decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)
            return decrypted
        return None

    return decrypt_dpapi(encrypted_key)


def decrypt_cookie_value(encrypted_value, key):
    """Decrypt a Chrome/Brave cookie value."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        # Check if encrypted with AES-GCM (starts with 'v10' or 'v11')
        if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v11':
            # Nonce is 12 bytes after version prefix
            nonce = encrypted_value[3:15]
            ciphertext = encrypted_value[15:]

            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode('utf-8')
        else:
            # Try DPAPI decryption for older format
            import ctypes
            import ctypes.wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ('cbData', ctypes.wintypes.DWORD),
                    ('pbData', ctypes.POINTER(ctypes.c_char))
                ]

            blob_in = DATA_BLOB(len(encrypted_value), ctypes.create_string_buffer(encrypted_value, len(encrypted_value)))
            blob_out = DATA_BLOB()

            if ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
            ):
                decrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return decrypted.decode('utf-8')
    except Exception as e:
        print(f"Decryption error: {e}")

    return ""


def extract_brave_cookies():
    """Extract Twitter cookies from Brave browser."""
    import os
    import sqlite3
    import shutil
    import tempfile

    # Get encryption key first
    try:
        key = get_encryption_key()
        print(f"Got encryption key")
    except Exception as e:
        print(f"Could not get encryption key: {e}")
        key = None

    brave_user_data = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data")

    # Find all possible cookie locations
    cookie_paths = []

    # Check Profile directories
    import glob
    for profile_dir in glob.glob(os.path.join(brave_user_data, "Profile*")):
        cookie_path = os.path.join(profile_dir, "Network", "Cookies")
        if os.path.exists(cookie_path):
            cookie_paths.append(cookie_path)

    # Also check Default
    default_cookie = os.path.join(brave_user_data, "Default", "Network", "Cookies")
    if os.path.exists(default_cookie):
        cookie_paths.append(default_cookie)

    all_cookies = []

    for cookie_path in cookie_paths:
        if not os.path.exists(cookie_path):
            continue

        # Copy the cookie file (it's locked while browser is running)
        temp_dir = tempfile.mkdtemp()
        temp_cookie = os.path.join(temp_dir, "Cookies")

        try:
            shutil.copy2(cookie_path, temp_cookie)

            conn = sqlite3.connect(temp_cookie)
            cursor = conn.cursor()

            # Get Twitter/X cookies - include encrypted_value column
            cursor.execute("""
                SELECT name, value, encrypted_value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key LIKE '%twitter.com%' OR host_key LIKE '%x.com%'
            """)

            for row in cursor.fetchall():
                name = row[0]
                value = row[1]
                encrypted_value = row[2]
                domain = row[3]
                path = row[4]
                expires = row[5]
                is_secure = row[6]
                is_httponly = row[7]

                # Decrypt the value if needed
                if not value and encrypted_value and key:
                    value = decrypt_cookie_value(encrypted_value, key)

                if value:  # Only add cookies with values
                    cookie = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path,
                        "expires": expires / 1000000 - 11644473600 if expires else -1,
                        "secure": bool(is_secure),
                        "httpOnly": bool(is_httponly)
                    }
                    all_cookies.append(cookie)

            conn.close()
        except Exception as e:
            print(f"Error reading cookies from {cookie_path}: {e}")
        finally:
            # Clean up temp file
            try:
                os.remove(temp_cookie)
                os.rmdir(temp_dir)
            except:
                pass

    return all_cookies


def save_cookies_to_file(cookies):
    """Save cookies to a JSON file."""
    # Convert to Playwright format
    playwright_cookies = []
    for cookie in cookies:
        pc = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "secure": cookie.get("secure", False),
            "httpOnly": cookie.get("httpOnly", False),
        }
        if cookie.get("expires") and cookie["expires"] > 0:
            pc["expires"] = cookie["expires"]
        playwright_cookies.append(pc)

    with open(COOKIES_FILE, 'w') as f:
        json.dump(playwright_cookies, f, indent=2)

    return playwright_cookies


async def setup_browser():
    """Extract cookies from Brave and set up for tweeting."""
    print("=" * 50)
    print("Extracting Twitter cookies from Brave browser...")
    print("(Make sure Brave is CLOSED for this to work)")
    print("=" * 50)

    cookies = extract_brave_cookies()

    if not cookies:
        print("\nNo Twitter cookies found!")
        print("Make sure you're logged into Twitter/X in Brave browser.")
        print("Close Brave completely and try again.")
        return

    # Filter for important auth cookies
    auth_cookies = [c for c in cookies if c["name"] in ["auth_token", "ct0", "twid"]]

    if not auth_cookies:
        print("\nFound cookies but no auth tokens!")
        print("Make sure you're logged into Twitter/X.")
        return

    saved = save_cookies_to_file(cookies)
    print(f"\nExtracted {len(cookies)} cookies ({len(auth_cookies)} auth cookies)")
    print(f"Saved to: {COOKIES_FILE}")
    print("\nSetup complete! You can now tweet using:")
    print("  python twitter_browser.py tweet <your message>")

    # Test the cookies
    print("\nTesting cookies...")
    async with async_playwright() as p:
        import os

        # Use Brave browser executable
        brave_path = os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe")
        if not os.path.exists(brave_path):
            brave_path = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")

        launch_args = {"headless": False}
        if os.path.exists(brave_path):
            launch_args["executable_path"] = brave_path
            print(f"Using Brave browser at: {brave_path}")

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context()

        # Add cookies
        await context.add_cookies(saved)

        page = await context.new_page()
        await page.goto("https://x.com/home")
        await asyncio.sleep(3)

        # Check if logged in
        url = page.url
        if "login" in url.lower():
            print("\nCookies didn't work - you may need to re-login to Brave.")
            print("Close Brave, open it, log into Twitter, close Brave, try again.")
        else:
            print("\nSuccess! You're logged in. Close the browser to finish.")

        try:
            await page.wait_for_event("close", timeout=60000)
        except:
            pass

        await browser.close()


async def tweet_text(text: str) -> dict:
    """Post a tweet using browser automation."""
    import os

    # Check for saved cookies
    if not COOKIES_FILE.exists():
        return {
            "success": False,
            "error": "No cookies found. Run: python twitter_browser.py setup"
        }

    # Load cookies
    with open(COOKIES_FILE, 'r') as f:
        cookies = json.load(f)

    async with async_playwright() as p:
        try:
            # Use Brave browser
            brave_path = os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe")
            if not os.path.exists(brave_path):
                brave_path = os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")

            launch_args = {"headless": True}  # Hidden browser - no window
            if os.path.exists(brave_path):
                launch_args["executable_path"] = brave_path

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})

            # Add cookies before navigating
            await context.add_cookies(cookies)

            page = await context.new_page()

            # Go to Twitter home
            await page.goto("https://x.com/home", timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            # Check if we got redirected to login
            if "login" in page.url.lower():
                await context.close()
                await browser.close()
                return {
                    "success": False,
                    "error": "Not logged in. Cookies may have expired. Please get fresh cookies from Brave."
                }

            await asyncio.sleep(3)

            # Find the tweet compose box
            # Try multiple selectors since Twitter changes often
            selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[aria-label="Post text"]',
                '[role="textbox"]',
                '.public-DraftEditor-content'
            ]

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
                return {
                    "success": False,
                    "error": "Could not find tweet compose box. Twitter UI may have changed."
                }

            # Click and type the tweet
            await compose_box.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type(text, delay=50)
            await asyncio.sleep(1)

            # Find and click the Post button
            post_selectors = [
                '[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButton"]',
                'button:has-text("Post")',
                'button:has-text("Tweet")'
            ]

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
                return {
                    "success": False,
                    "error": "Could not find Post button."
                }

            await post_button.click()
            await asyncio.sleep(3)  # Wait for tweet to post

            await context.close()
            await browser.close()

            return {
                "success": True,
                "tweet": text,
                "method": "browser_automation"
            }

        except Exception as e:
            try:
                await browser.close()
            except:
                pass
            return {
                "success": False,
                "error": str(e)
            }


async def main():
    """Main function for testing."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python twitter_browser.py setup     - Set up browser session (log in)")
        print("  python twitter_browser.py tweet <text>  - Post a tweet")
        return

    command = sys.argv[1]

    if command == "setup":
        await setup_browser()
    elif command == "tweet":
        if len(sys.argv) < 3:
            print("Please provide tweet text")
            return
        text = " ".join(sys.argv[2:])
        result = await tweet_text(text)
        # Silent mode - only print if error
        if not result.get("success"):
            print(f"Error: {result.get('error')}")
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
