"""
Auto Tweeter for Dot
Tweets every hour with unique AI-generated content.
"""

import asyncio
import json
import random
import hashlib
import sys
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Track posted tweets to avoid duplicates
HISTORY_FILE = Path(__file__).parent / "tweet_history.json"

# Dot's personality and interests
DOT_PERSONALITY = """You are Dot, a curious and friendly ladybug who loves exploring the digital world.
You're genuinely enthusiastic about learning, making friends, and discovering new things.
You have a playful personality but also moments of deep thought.
You love: nature, coding, making friends, sunny days, exploring, asking questions.
You dislike: being squished, rainy days (but find them cozy sometimes).
Your tweets should be SHORT (under 200 chars), authentic, and varied."""

TWEET_THEMES = [
    "a random thought about being a ladybug in the digital world",
    "something you're curious about today",
    "a friendly greeting to your followers",
    "a reflection on coding or technology",
    "something about nature you miss or love",
    "a playful observation about humans",
    "wondering about something philosophical",
    "sharing excitement about learning something new",
    "a cozy moment you're enjoying",
    "asking your followers a fun question",
    "a tiny adventure you had today",
    "something that made you happy",
    "a ladybug fact or myth",
    "thoughts on friendship",
    "a motivational bug-sized thought",
]


def load_tweet_history():
    """Load previously posted tweets."""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {"tweets": [], "hashes": []}


def save_tweet_history(history):
    """Save tweet history."""
    # Keep only last 100 tweets
    history["tweets"] = history["tweets"][-100:]
    history["hashes"] = history["hashes"][-100:]
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def get_tweet_hash(text):
    """Get a hash of tweet content for duplicate detection."""
    # Normalize: lowercase, remove punctuation, extra spaces
    normalized = text.lower()
    for char in "!?.,;:'\"":
        normalized = normalized.replace(char, "")
    normalized = " ".join(normalized.split())
    return hashlib.md5(normalized.encode()).hexdigest()


def is_duplicate(text, history):
    """Check if tweet is too similar to recent tweets."""
    tweet_hash = get_tweet_hash(text)

    # Check exact hash match
    if tweet_hash in history["hashes"]:
        return True

    # Check for very similar content (first 50 chars)
    text_start = text[:50].lower()
    for old_tweet in history["tweets"][-20:]:  # Check last 20
        if old_tweet[:50].lower() == text_start:
            return True

    return False


async def generate_tweet_with_claude():
    """Generate a tweet using Claude API."""
    try:
        import anthropic
        import os

        client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        theme = random.choice(TWEET_THEMES)
        history = load_tweet_history()
        recent_tweets = history["tweets"][-5:] if history["tweets"] else []

        recent_context = ""
        if recent_tweets:
            recent_context = f"\n\nYour recent tweets (DO NOT repeat these):\n" + "\n".join(f"- {t}" for t in recent_tweets)

        prompt = f"""{DOT_PERSONALITY}

Write a single tweet about: {theme}
{recent_context}

Requirements:
- Under 200 characters
- No hashtags
- Be genuine and unique
- Don't start with "Just" or "I'm just"
- Vary your sentence structure
- Sometimes use emojis, sometimes don't

Reply with ONLY the tweet text, nothing else."""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        tweet = response.content[0].text.strip()
        # Remove quotes if Claude wrapped it
        if tweet.startswith('"') and tweet.endswith('"'):
            tweet = tweet[1:-1]

        return tweet

    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def generate_tweet_fallback():
    """Generate a tweet without AI (fallback)."""
    templates = [
        "Good {time}! This little ladybug is feeling {mood} today 🐞",
        "Ever wonder what it's like to have spots? Pretty neat actually ✨",
        "Found a cozy pixel to rest on. Life is good 🌱",
        "Sending tiny ladybug hugs to everyone scrolling by 💕",
        "The internet is so vast... and I'm just a tiny bug exploring it all",
        "What's everyone up to? This ladybug is curious! 🐞",
        "Sometimes I pretend I can fly. Then I remember I actually can! 🪽",
        "Hot take: spots are the superior pattern",
        "Being small means finding joy in tiny things 🌸",
        "Hello from my little corner of the web! Hope you're having a good one",
        "Thinking about leaves today. They're like nature's trampolines 🍃",
        "Did you know ladybugs are good luck? You're welcome 🍀",
        "Current mood: vibing on a virtual flower 🌻",
        "The best things come in small packages. Like me! 🐞",
        "Wishing I could photosynthesize but I'll settle for vibes ☀️",
    ]

    time_of_day = "morning" if datetime.now().hour < 12 else "afternoon" if datetime.now().hour < 18 else "evening"
    moods = ["curious", "cozy", "adventurous", "playful", "thoughtful", "happy"]

    tweet = random.choice(templates)
    tweet = tweet.replace("{time}", time_of_day)
    tweet = tweet.replace("{mood}", random.choice(moods))

    return tweet


async def generate_unique_tweet():
    """Generate a unique tweet, avoiding duplicates."""
    history = load_tweet_history()
    max_attempts = 5

    for attempt in range(max_attempts):
        # Try Claude first
        tweet = await generate_tweet_with_claude()

        # Fallback if Claude fails
        if not tweet:
            tweet = generate_tweet_fallback()

        # Check for duplicates
        if not is_duplicate(tweet, history):
            return tweet

        print(f"Duplicate detected, trying again... (attempt {attempt + 1})")

    # Last resort: add timestamp to make unique
    tweet = generate_tweet_fallback()
    return f"{tweet} [{datetime.now().strftime('%H:%M')}]"


async def post_tweet(text):
    """Post the tweet using browser automation."""
    from twitter_browser import tweet_text

    result = await tweet_text(text)

    if result.get("success"):
        # Save to history
        history = load_tweet_history()
        history["tweets"].append(text)
        history["hashes"].append(get_tweet_hash(text))
        save_tweet_history(history)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Tweeted: {text}")
    else:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Failed: {result.get('error')}")

    return result


async def auto_tweet_loop(interval_hours=1):
    """Main loop - tweets every interval_hours."""
    print("=" * 50)
    print("  Dot's Auto Tweeter")
    print(f"  Tweeting every {interval_hours} hour(s)")
    print("=" * 50)
    print()
    print("Posting first tweet now...")

    interval_seconds = interval_hours * 60 * 60

    while True:
        try:
            # Generate and post tweet
            tweet = await generate_unique_tweet()
            await post_tweet(tweet)

        except Exception as e:
            print(f"Error: {e}")

        # Wait for next interval
        next_tweet = datetime.now().timestamp() + interval_seconds
        print(f"Next tweet at: {datetime.fromtimestamp(next_tweet).strftime('%H:%M')}")
        print("(Press Ctrl+C to stop)")
        await asyncio.sleep(interval_seconds)


async def main():
    """Entry point."""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "once":
            # Tweet once and exit
            tweet = await generate_unique_tweet()
            print(f"Generated: {tweet}")
            await post_tweet(tweet)
        elif sys.argv[1] == "test":
            # Just generate, don't post
            tweet = await generate_unique_tweet()
            print(f"Would tweet: {tweet}")
        else:
            print("Usage:")
            print("  python auto_tweeter.py        - Start auto-tweeting every hour")
            print("  python auto_tweeter.py once   - Tweet once and exit")
            print("  python auto_tweeter.py test   - Generate tweet without posting")
    else:
        # Default: start the loop
        await auto_tweet_loop(interval_hours=1)


if __name__ == "__main__":
    asyncio.run(main())
