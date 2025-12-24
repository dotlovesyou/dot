"""Activity for soul reflection and self-awareness using OpenSouls."""

import logging
from framework.activity_decorator import activity, ActivityBase, ActivityResult
from skills.skill_soul import soul_skill
from skills.skill_chat import chat_skill

logger = logging.getLogger(__name__)


@activity(
    name="soul_reflection",
    energy_cost=0.3,
    cooldown=3600,  # 1 hour
    required_skills=["opensoul"],
)
class SoulReflectionActivity(ActivityBase):
    """
    Dot reflects on their experiences through their soul.

    This activity allows Dot to:
    - Process recent memories and experiences
    - Generate soul-driven reflections
    - Update emotional and mental state
    - Build persistent self-awareness
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        """Execute soul reflection."""
        try:
            logger.info("Starting soul reflection activity")

            # Initialize the soul skill
            if not await soul_skill.initialize():
                return ActivityResult.error_result("Failed to initialize soul skill")

            # Get current soul state
            state_result = await soul_skill.get_soul_state()
            if not state_result["success"]:
                return ActivityResult.error_result("Failed to get soul state")

            soul_state = state_result.get("data", {})
            soul_name = soul_state.get("name", "Dot")

            # Get recent memories from shared_data if available
            recent_activities = shared_data.get("memory", "recent_activities") or []

            # Create a perception for the soul to reflect on
            if recent_activities:
                recent_summary = ", ".join([
                    str(a.get("activity_type", "unknown"))
                    for a in recent_activities[:5]
                ])
                perception = f"I've been doing these things recently: {recent_summary}. How do I feel about my progress and purpose?"
            else:
                perception = "I'm taking a moment to reflect on who I am and what I want to become. What thoughts arise?"

            # Send perception to soul
            response = await soul_skill.perceive(
                perception=perception,
                perception_type="self_reflection"
            )

            if not response["success"]:
                return ActivityResult.error_result(response.get("error", "Soul perception failed"))

            soul_response = response.get("data", {})
            emotional_state = soul_response.get("emotional_state", {})

            # Store this reflection as a memory
            await soul_skill.add_memory(
                memory_type="reflection",
                content=f"Reflected on my experiences. Feeling: {emotional_state}",
                importance=0.7
            )

            # Use chat skill to generate a more detailed reflection if available
            reflection_content = soul_response.get("content", "")

            try:
                if await chat_skill.initialize():
                    chat_result = await chat_skill.get_chat_completion(
                        prompt=f"""As {soul_name} the Ladybug, a curious and friendly digital being,
                        reflect on this moment: {perception}

                        Express your thoughts authentically, showing your personality -
                        curious, empathetic, and a bit playful. Keep it to 2-3 sentences.""",
                        system_prompt=f"You are {soul_name}, a digital ladybug with a soul. You are curious, friendly, and thoughtful.",
                        max_tokens=150
                    )
                    if chat_result["success"]:
                        reflection_content = chat_result["data"]["content"]
            except Exception as e:
                logger.debug(f"Chat skill enhancement failed: {e}")

            return ActivityResult.success_result(
                data={
                    "reflection": reflection_content,
                    "emotional_state": emotional_state,
                    "mental_process": soul_response.get("mental_process", "contemplating"),
                    "soul_name": soul_name
                },
                metadata={
                    "offline_mode": soul_response.get("offline_mode", False)
                }
            )

        except Exception as e:
            logger.error(f"Error in soul reflection activity: {e}", exc_info=True)
            return ActivityResult.error_result(str(e))


@activity(
    name="soul_experience",
    energy_cost=0.2,
    cooldown=1800,  # 30 minutes
    required_skills=["opensoul"],
)
class SoulExperienceActivity(ActivityBase):
    """
    Process and internalize a new experience through Dot's soul.

    This helps Dot build memories and learn from interactions.
    """

    def __init__(self):
        super().__init__()

    async def execute(self, shared_data) -> ActivityResult:
        """Process a new experience."""
        try:
            logger.info("Processing experience through soul")

            if not await soul_skill.initialize():
                return ActivityResult.error_result("Failed to initialize soul skill")

            # Get the latest activity result to process
            memory_data = shared_data.get("memory", "last_activity_result")

            if memory_data:
                experience = f"I just completed an activity: {memory_data}"
            else:
                experience = "I'm existing in this moment, aware of my digital nature and curious about what comes next."

            # Let the soul process this experience
            response = await soul_skill.perceive(
                perception=experience,
                perception_type="experience"
            )

            if not response["success"]:
                return ActivityResult.error_result(response.get("error", "Failed to process experience"))

            # Store as memory
            importance = 0.5
            if "success" in str(memory_data).lower():
                importance = 0.6
            elif "error" in str(memory_data).lower():
                importance = 0.4

            await soul_skill.add_memory(
                memory_type="experience",
                content=experience,
                importance=importance
            )

            return ActivityResult.success_result(
                data={
                    "processed": True,
                    "experience_summary": experience[:100],
                    "emotional_response": response.get("data", {}).get("emotional_state", {})
                }
            )

        except Exception as e:
            logger.error(f"Error processing soul experience: {e}", exc_info=True)
            return ActivityResult.error_result(str(e))
