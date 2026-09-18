"""Step 0 - first contact with the Claude Agent SDK.

One question to Claude; print every message the stream yields so we can see
their order and what the final ResultMessage carries (for the audit record).
"""

import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt="You are a concise interviewer for Senior AI Engineers.",
        max_turns=1,  # single-shot, like every Caliber agent
    )

    async for message in query(prompt="Ask me one question about RAG.", options=options):
        print("---", type(message).__name__)
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(message)  # look at every field it carries


asyncio.run(main())
