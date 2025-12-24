"""
Dot's Soul Server

A lightweight Python-based soul server that provides Dot with:
- Persistent memory across interactions
- Emotional state tracking
- Mental process transitions
- Personality-driven responses

This can run standalone or integrate with the full OpenSouls engine later.
"""

import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Storage paths
STORAGE_DIR = Path(__file__).parent / "storage"
MEMORY_FILE = STORAGE_DIR / "working_memory.json"
STATE_FILE = STORAGE_DIR / "soul_state.json"


class DotSoul:
    """Dot the Ladybug's Soul"""

    def __init__(self):
        self.name = "Dot"
        self.working_memory: List[Dict[str, Any]] = []
        self.long_term_memory: List[Dict[str, Any]] = []
        self.emotional_state = {
            "curiosity": 0.9,
            "friendliness": 0.8,
            "energy": 0.8,
            "playfulness": 0.6,
            "contentment": 0.7
        }
        self.mental_process = "idle"
        self.personality = {
            "friendliness": 0.8,
            "creativity": 0.7,
            "curiosity": 0.9,
            "empathy": 0.75,
            "humor": 0.6,
            "formality": 0.5,
            "emotional_stability": 0.8
        }
        self._load_state()

    def _load_state(self):
        """Load persisted state from disk."""
        STORAGE_DIR.mkdir(exist_ok=True)

        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    data = json.load(f)
                    self.working_memory = data.get("working_memory", [])
                    self.long_term_memory = data.get("long_term_memory", [])
                logger.info(f"Loaded {len(self.working_memory)} working memories")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")

        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.emotional_state = data.get("emotional_state", self.emotional_state)
                    self.mental_process = data.get("mental_process", "idle")
                logger.info(f"Loaded soul state: {self.mental_process}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        """Persist state to disk."""
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump({
                    "working_memory": self.working_memory[-100:],  # Keep last 100
                    "long_term_memory": self.long_term_memory[-500:]  # Keep last 500
                }, f, indent=2)

            with open(STATE_FILE, "w") as f:
                json.dump({
                    "emotional_state": self.emotional_state,
                    "mental_process": self.mental_process
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def perceive(self, content: str, perception_type: str = "observation") -> Dict[str, Any]:
        """
        Process a perception and generate a soul response.
        """
        # Add to working memory
        memory_entry = {
            "content": content,
            "type": perception_type,
            "timestamp": datetime.now().isoformat(),
            "emotional_context": self.emotional_state.copy()
        }
        self.working_memory.append(memory_entry)

        # Update emotional state based on perception
        self._process_emotion(content, perception_type)

        # Determine mental process
        self._update_mental_process(content, perception_type)

        # Generate response
        response = self._generate_response(content, perception_type)

        # Save state
        self._save_state()

        return {
            "response": response,
            "emotional_state": self.emotional_state.copy(),
            "mental_process": self.mental_process
        }

    def _process_emotion(self, content: str, perception_type: str):
        """Update emotional state based on perception."""
        content_lower = content.lower()

        # Positive triggers
        if any(word in content_lower for word in ["happy", "love", "great", "wonderful", "amazing", "thank"]):
            self.emotional_state["contentment"] = min(1.0, self.emotional_state["contentment"] + 0.1)
            self.emotional_state["friendliness"] = min(1.0, self.emotional_state["friendliness"] + 0.05)

        # Curiosity triggers
        if any(word in content_lower for word in ["?", "what", "how", "why", "curious", "wonder", "interesting"]):
            self.emotional_state["curiosity"] = min(1.0, self.emotional_state["curiosity"] + 0.1)

        # Energy management
        if perception_type == "self_reflection":
            self.emotional_state["energy"] = max(0.3, self.emotional_state["energy"] - 0.05)
        elif perception_type == "experience":
            self.emotional_state["energy"] = max(0.2, self.emotional_state["energy"] - 0.02)

        # Playfulness triggers
        if any(word in content_lower for word in ["fun", "play", "game", "joke", "laugh"]):
            self.emotional_state["playfulness"] = min(1.0, self.emotional_state["playfulness"] + 0.15)

    def _update_mental_process(self, content: str, perception_type: str):
        """Determine current mental process based on context."""
        content_lower = content.lower()

        if perception_type == "self_reflection":
            self.mental_process = "contemplating"
        elif "?" in content or any(word in content_lower for word in ["what", "how", "why"]):
            self.mental_process = "curious"
        elif any(word in content_lower for word in ["fun", "play", "game"]):
            self.mental_process = "playful"
        elif any(word in content_lower for word in ["help", "support", "feel"]):
            self.mental_process = "empathetic"
        elif self.emotional_state["energy"] < 0.3:
            self.mental_process = "resting"
        else:
            self.mental_process = "engaged"

    def _generate_response(self, content: str, perception_type: str) -> str:
        """Generate a soul response based on current state."""
        process_responses = {
            "contemplating": f"*{self.name} reflects thoughtfully, antennae gently moving*",
            "curious": f"*{self.name}'s eyes light up with curiosity*",
            "playful": f"*{self.name} does a little happy dance on their leaf*",
            "empathetic": f"*{self.name} moves closer, radiating warmth*",
            "resting": f"*{self.name} settles down peacefully, conserving energy*",
            "engaged": f"*{self.name} focuses attentively*",
            "idle": f"*{self.name} waits patiently, observing the world*"
        }
        return process_responses.get(self.mental_process, f"*{self.name} is present*")

    def transition(self, new_state: str, reason: str = "") -> Dict[str, Any]:
        """Transition to a new mental state."""
        old_state = self.mental_process
        self.mental_process = new_state

        # Adjust emotions based on transition
        if new_state == "playful":
            self.emotional_state["playfulness"] = min(1.0, self.emotional_state["playfulness"] + 0.2)
        elif new_state == "resting":
            self.emotional_state["energy"] = min(1.0, self.emotional_state["energy"] + 0.1)

        self._save_state()

        return {
            "success": True,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current soul state."""
        return {
            "name": self.name,
            "mental_process": self.mental_process,
            "emotional_state": self.emotional_state.copy(),
            "personality": self.personality.copy(),
            "working_memory_size": len(self.working_memory),
            "long_term_memory_size": len(self.long_term_memory)
        }

    def add_memory(self, memory_type: str, content: str, importance: float = 0.5) -> Dict[str, Any]:
        """Add a memory to the soul."""
        entry = {
            "type": memory_type,
            "content": content,
            "importance": importance,
            "timestamp": datetime.now().isoformat()
        }

        if importance >= 0.7:
            self.long_term_memory.append(entry)
        else:
            self.working_memory.append(entry)

        self._save_state()

        return {
            "success": True,
            "stored_in": "long_term" if importance >= 0.7 else "working",
            "total_memories": len(self.working_memory) + len(self.long_term_memory)
        }


# Create global soul instance
dot_soul = DotSoul()


# HTTP API handlers
async def health_handler(request):
    """Health check endpoint."""
    return web.json_response({"status": "ok", "soul": "Dot"})


async def perceive_handler(request):
    """Handle perception requests."""
    try:
        data = await request.json()
        perception = data.get("perception", "")
        perception_type = data.get("type", "observation")

        result = dot_soul.perceive(perception, perception_type)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def transition_handler(request):
    """Handle state transition requests."""
    try:
        data = await request.json()
        new_state = data.get("new_state", "idle")
        reason = data.get("reason", "")

        result = dot_soul.transition(new_state, reason)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def state_handler(request):
    """Get current soul state."""
    try:
        state = dot_soul.get_state()
        return web.json_response(state)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def memory_handler(request):
    """Add a memory."""
    try:
        data = await request.json()
        memory_type = data.get("type", "experience")
        content = data.get("content", "")
        importance = data.get("importance", 0.5)

        result = dot_soul.add_memory(memory_type, content, importance)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


def create_app():
    """Create the web application."""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/souls/dot/state", state_handler)
    app.router.add_post("/souls/dot/perceive", perceive_handler)
    app.router.add_post("/souls/dot/transition", transition_handler)
    app.router.add_post("/souls/dot/memory", memory_handler)
    return app


if __name__ == "__main__":
    print("=" * 50)
    print("  Dot's Soul Server")
    print("  A curious ladybug with a genuine soul")
    print("=" * 50)
    print()
    print(f"Starting soul server on http://localhost:3000")
    print(f"Soul name: {dot_soul.name}")
    print(f"Mental process: {dot_soul.mental_process}")
    print(f"Emotional state: {dot_soul.emotional_state}")
    print()

    app = create_app()
    web.run_app(app, host="localhost", port=3000)
