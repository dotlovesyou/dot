"""
OpenSouls Integration Skill

This skill connects Dot to the OpenSouls Soul Engine, giving Dot
a persistent soul with memory, personality, and genuine agency.

The Soul Engine runs as a separate Node.js service. This skill
communicates with it via HTTP/WebSocket.
"""

import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List

from framework.api_management import api_manager
from framework.main import DigitalBeing

logger = logging.getLogger(__name__)


class SoulSkill:
    """
    Skill for connecting to OpenSouls Soul Engine.

    The Soul Engine provides:
    - WorkingMemory: Persistent memory across interactions
    - CognitiveSteps: Personality-driven response generation
    - MentalProcesses: Dynamic behavioral states
    """

    def __init__(self):
        self.skill_name = "opensoul"
        self.required_api_keys = ["OPENAI"]  # Soul Engine uses OpenAI under the hood
        api_manager.register_required_keys(self.skill_name, self.required_api_keys)

        self._initialized = False
        self.soul_engine_url: str = "http://localhost:3000"
        self.soul_name: str = "dot"
        self._session: Optional[aiohttp.ClientSession] = None
        self._working_memory: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """
        Initialize connection to the Soul Engine.
        """
        try:
            being = DigitalBeing()
            being.initialize()
            skill_cfg = being.configs.get("skills_config", {}).get("opensoul", {})

            self.soul_engine_url = skill_cfg.get("soul_engine_url", "http://localhost:3000")
            self.soul_name = skill_cfg.get("soul_name", "dot")

            # Get OpenAI key for Soul Engine
            api_key = await api_manager.get_api_key(self.skill_name, "OPENAI")
            if not api_key:
                logger.warning("No OpenAI key found for Soul Engine")

            self._session = aiohttp.ClientSession()

            # Check if Soul Engine is running
            try:
                async with self._session.get(f"{self.soul_engine_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        logger.info(f"Connected to Soul Engine at {self.soul_engine_url}")
                        self._initialized = True
                        return True
            except Exception as e:
                logger.warning(f"Soul Engine not running at {self.soul_engine_url}: {e}")
                # Still initialize - we can work in offline mode
                self._initialized = True
                return True

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Soul skill: {e}", exc_info=True)
            self._initialized = False
            return False

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def perceive(self, perception: str, perception_type: str = "user_message") -> Dict[str, Any]:
        """
        Send a perception to the soul and get a response.

        Perceptions are inputs the soul receives - messages, events, observations.
        The soul processes these through its cognitive steps and mental processes.

        Args:
            perception: The content of what the soul perceives
            perception_type: Type of perception (user_message, system_event, observation)

        Returns:
            Soul's response with content, emotional state, and metadata
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "Soul skill not initialized",
                "data": None
            }

        try:
            # Add to working memory
            self._working_memory.append({
                "type": perception_type,
                "content": perception,
                "timestamp": asyncio.get_event_loop().time()
            })

            # Try to communicate with Soul Engine
            if self._session:
                try:
                    payload = {
                        "soul": self.soul_name,
                        "perception": perception,
                        "type": perception_type,
                        "memory": self._working_memory[-10:]  # Last 10 memories for context
                    }

                    async with self._session.post(
                        f"{self.soul_engine_url}/souls/{self.soul_name}/perceive",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return {
                                "success": True,
                                "data": {
                                    "content": data.get("response", ""),
                                    "emotional_state": data.get("emotional_state", {}),
                                    "mental_process": data.get("mental_process", "default"),
                                    "soul_name": self.soul_name
                                },
                                "error": None
                            }
                except Exception as e:
                    logger.debug(f"Soul Engine request failed, using fallback: {e}")

            # Fallback: Return a soul-like response based on Dot's character
            return await self._generate_soul_response(perception)

        except Exception as e:
            logger.error(f"Error in soul perception: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    async def _generate_soul_response(self, perception: str) -> Dict[str, Any]:
        """
        Generate a soul-like response when Soul Engine is not available.
        This uses Dot's character config to maintain personality consistency.
        """
        try:
            being = DigitalBeing()
            being.initialize()
            character = being.configs.get("character_config", {})

            personality = character.get("personality", {})
            name = character.get("name", "Dot")

            # Determine emotional state based on personality
            emotional_state = {
                "curiosity": personality.get("curiosity", 0.9),
                "friendliness": personality.get("friendliness", 0.8),
                "energy": personality.get("emotional_stability", 0.8)
            }

            return {
                "success": True,
                "data": {
                    "content": f"*{name} considers this thoughtfully*",
                    "emotional_state": emotional_state,
                    "mental_process": "contemplating",
                    "soul_name": self.soul_name,
                    "offline_mode": True
                },
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    async def update_mental_state(self, new_state: str, reason: str = "") -> Dict[str, Any]:
        """
        Transition the soul to a new mental state/process.

        Mental processes define behavioral modes like:
        - contemplating: Deep thought mode
        - playful: Light, fun interactions
        - focused: Task-oriented behavior
        - curious: Exploration mode
        - resting: Low energy state
        """
        if not self._initialized:
            return {"success": False, "error": "Soul skill not initialized"}

        try:
            if self._session:
                try:
                    payload = {
                        "soul": self.soul_name,
                        "new_state": new_state,
                        "reason": reason
                    }

                    async with self._session.post(
                        f"{self.soul_engine_url}/souls/{self.soul_name}/transition",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            return {"success": True, "state": new_state}
                except Exception:
                    pass

            # Offline mode - just track locally
            return {"success": True, "state": new_state, "offline_mode": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_soul_state(self) -> Dict[str, Any]:
        """Get the current state of the soul."""
        if not self._initialized:
            return {"success": False, "error": "Soul skill not initialized"}

        try:
            if self._session:
                try:
                    async with self._session.get(
                        f"{self.soul_engine_url}/souls/{self.soul_name}/state",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return {"success": True, "data": data}
                except Exception:
                    pass

            # Return local state
            being = DigitalBeing()
            being.initialize()
            character = being.configs.get("character_config", {})

            return {
                "success": True,
                "data": {
                    "name": character.get("name", "Dot"),
                    "personality": character.get("personality", {}),
                    "working_memory_size": len(self._working_memory),
                    "offline_mode": True
                }
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_memory(self, memory_type: str, content: str, importance: float = 0.5) -> Dict[str, Any]:
        """
        Add a memory to the soul's working memory.

        Args:
            memory_type: Category of memory (experience, learning, emotion, observation)
            content: The memory content
            importance: How significant this memory is (0-1)
        """
        memory_entry = {
            "type": memory_type,
            "content": content,
            "importance": importance,
            "timestamp": asyncio.get_event_loop().time()
        }

        self._working_memory.append(memory_entry)

        # Keep working memory bounded
        if len(self._working_memory) > 100:
            # Keep important memories
            self._working_memory.sort(key=lambda x: x.get("importance", 0), reverse=True)
            self._working_memory = self._working_memory[:50]

        return {"success": True, "memory_count": len(self._working_memory)}


# Global instance
soul_skill = SoulSkill()
