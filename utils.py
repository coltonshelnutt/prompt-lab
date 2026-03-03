"""Utilities — report generation and metric formatting."""

from datetime import datetime


def generate_report(
    prompts: list[str],
    results: list[dict],
    user_input: str,
    model: str,
) -> str:
    """Build a markdown comparison report ready for download.

    Args:
        prompts:    List of system prompt strings (errors already filtered out).
        results:    Corresponding evaluated result dicts.
        user_input: The shared test input used for all prompts.
        model:      Model ID string.

    Returns:
        A multi-line markdown string.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        "# Prompt Lab — Comparison Report",
        "",
        f"**Generated:** {timestamp}  ",
        f"**Model:** `{model}`  ",
        f"**Prompts tested:** {len(prompts)}",
        "",
        "## Test Input",
        "",
        f"> {user_input}",
        "",
        "---",
        "",
    ]

    for i, (prompt, result) in enumerate(zip(prompts, results), start=1):
        lines += [
            f"## Prompt {i}",
            "",
            "**System prompt:**",
            "",
            "```",
            prompt.strip(),
            "```",
            "",
            "**Metrics:**",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Response time | `{result['response_time']:.2f}s` |",
            f"| Word count | `{result['word_count']}` |",
            f"| Character count | `{result['char_count']}` |",
            f"| Output tokens | `{result['output_tokens']}` |",
            f"| Input tokens | `{result['input_tokens']}` |",
            f"| Stop reason | `{result['stop_reason']}` |",
            "",
            "**Response:**",
            "",
            result["response"].strip(),
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


def _truncate(text: str, max_len: int = 72) -> str:
    """Truncate a string with an ellipsis for display in tight spaces."""
    return text if len(text) <= max_len else text[:max_len].rstrip() + "…"
