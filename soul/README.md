# Dot's Soul

This directory contains Dot the Ladybug's soul definition for the [OpenSouls](https://github.com/opensouls/opensouls) Soul Engine.

## What is a Soul?

The Soul Engine creates AI beings with genuine personality, memory, and agency. Unlike simple chatbots, souls:

- Have persistent memory across interactions
- Experience emotional states
- Transition between mental processes
- Grow and evolve over time

## Running Dot's Soul

### Prerequisites

1. Install [Bun](https://bun.sh/) (JavaScript runtime)
2. Have an OpenAI API key

### Setup

```bash
cd soul
bun install
```

### Start the Soul Engine

```bash
bun run dev
```

This starts the Soul Engine locally at `http://localhost:3000`. The Dot digital being framework will automatically connect to it.

## Files

- `soul.ts` - Dot's soul definition (personality, mental processes, behaviors)
- `staticMemories/core.md` - Dot's foundational memories and identity
- `package.json` - Dependencies

## Integration with Dot Framework

The Python `skill_soul.py` in `my_digital_being/skills/` communicates with this Soul Engine to:

- Send perceptions (messages, events, observations)
- Receive soul-driven responses
- Update mental states
- Build persistent memories

When the Soul Engine isn't running, the skill falls back to using Dot's character config for personality-consistent responses.

## Customizing Dot's Soul

Edit `staticMemories/core.md` to change Dot's foundational memories and personality. Changes take effect immediately while the engine is running.
