"""Evaluator — enriches a runner result with text-quality metrics."""


def evaluate(result: dict) -> dict:
    """Compute word count and character count from a runner result dict.

    Args:
        result: dict returned by runner.run_prompt()

    Returns:
        The same dict with additional keys: word_count, char_count
    """
    text = result["response"]
    return {
        **result,
        "word_count": len(text.split()),
        "char_count": len(text),
    }
