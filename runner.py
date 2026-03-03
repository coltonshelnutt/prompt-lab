"""Claude API runner — executes a single prompt and returns raw metrics."""

import time

import anthropic
from dotenv import load_dotenv

load_dotenv()


def run_prompt(
    system_prompt: str,
    user_input: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 1024,
) -> dict:
    """Run one system prompt + user input against Claude.

    Uses streaming with get_final_message() to avoid HTTP timeouts on
    long responses (recommended for Opus 4.6 with large max_tokens).

    Returns:
        dict with keys: response, response_time, input_tokens,
                        output_tokens, stop_reason
    """
    client = anthropic.Anthropic()

    start = time.perf_counter()

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}],
    ) as stream:
        final = stream.get_final_message()

    elapsed = time.perf_counter() - start

    return {
        "response": final.content[0].text,
        "response_time": elapsed,
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "stop_reason": final.stop_reason,
    }
