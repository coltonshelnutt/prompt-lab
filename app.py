"""Prompt Lab — Streamlit UI for comparing Claude prompt variations."""

from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st

from evaluator import evaluate
from runner import run_prompt
from utils import generate_report

# ---------------------------------------------------------------------------
# Example content
# ---------------------------------------------------------------------------
EXAMPLE_INPUT = (
    "Explain the difference between supervised and unsupervised learning. "
    "Give me a concrete example of each."
)

EXAMPLE_PROMPTS = [
    # Prompt 1 — minimal / concise style
    "You are a helpful AI assistant. Answer clearly and concisely.",
    # Prompt 2 — structured / educator style
    (
        "You are an expert data science educator. When explaining concepts:\n"
        "- Start with a one-sentence definition\n"
        "- Use a real-world analogy before introducing technical details\n"
        "- Provide a concrete, practical example for each concept\n"
        "- End with a brief note on when to use each approach\n\n"
        "Keep explanations accessible to someone new to machine learning."
    ),
    # Prompt 3 — technical / code-oriented style
    (
        "You are a machine learning engineer explaining concepts to a software developer. "
        "Be precise and technical. For each concept, include a short Python snippet "
        "that illustrates the idea. Skip introductory padding and get straight to the point."
    ),
    # Prompt 4 — narrative / story-driven style
    (
        "You are a data science teacher who explains ideas through relatable real-world stories. "
        "For each concept, open with a 2–3 sentence scenario a non-technical person could picture, "
        "then connect it to the technical idea. Use plain language throughout and avoid jargon "
        "unless you define it immediately."
    ),
]

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Prompt Lab",
    page_icon="🧪",
    layout="wide",
)

# Override Streamlit's default red accent (#FF4B4B) with blue (#0068C9)
# across buttons, sliders, and input focus rings.
st.markdown(
    """
    <style>
    /* ── Primary button ─────────────────────────────────────── */
    button[kind="primary"] {
        background-color: #0068C9;
        border-color: #0068C9;
        color: white;
    }
    button[kind="primary"]:hover {
        background-color: #0054A3;
        border-color: #0054A3;
        color: white;
    }
    button[kind="primary"]:active {
        background-color: #003D7A;
        border-color: #003D7A;
        color: white;
    }

    /* ── Sidebar slider: blue thumb, white label ────────────── */
    [data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
        background-color: #0068C9 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderThumbValue"] {
        color: white !important;
    }

    /* ── Text areas & inputs: focus border/glow ─────────────── */
    /* base-web wraps each widget; :focus-within fires when the inner
       element is focused and is where Streamlit draws the border ring. */
    [data-baseweb="textarea"]:focus-within,
    [data-baseweb="base-input"]:focus-within {
        border-color: #0068C9 !important;
        box-shadow: 0 0 0 1px #0068C9 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — model & token config
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Config")
    st.divider()

    model = st.selectbox(
        "Model",
        options=["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"],
        index=0,
        help="All prompts are run against the same model.",
    )

    num_prompts: int = st.selectbox(
        "Number of Prompt Variations",
        options=[2, 3, 4],
        index=0,
    )

    max_tokens = st.slider(
        "Max Output Tokens",
        min_value=256,
        max_value=4096,
        value=1024,
        step=256,
        help="Maximum tokens Claude may generate per response.",
    )

    st.divider()
    st.markdown(
        "**Prompt Lab** lets you write 2–4 system prompt variations, "
        "fire them all in parallel against a shared test input, and "
        "compare the results side by side."
    )
    st.caption("Built with Claude + Streamlit")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🧪 Prompt Lab")
st.markdown(
    "Write **2–4 prompt variations**, enter a test input, hit **Run All**, "
    "and compare responses — response time, word count, and token usage included."
)

load_col, clear_col, _ = st.columns([1, 1, 6])

if load_col.button("📋  Load Example", use_container_width=True):
    st.session_state["user_input"] = EXAMPLE_INPUT
    for i, text in enumerate(EXAMPLE_PROMPTS):
        st.session_state[f"prompt_{i}"] = text
    for i in range(len(EXAMPLE_PROMPTS), 4):
        st.session_state[f"prompt_{i}"] = ""
    st.rerun()

if clear_col.button("🗑  Clear", use_container_width=True):
    st.session_state["user_input"] = ""
    for i in range(4):
        st.session_state[f"prompt_{i}"] = ""
    for key in ("results", "prompts", "run_input", "model"):
        st.session_state.pop(key, None)
    st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Test input
# ---------------------------------------------------------------------------
user_input = st.text_area(
    "Test Input",
    placeholder="Enter the user message you want to test all prompts against…",
    height=110,
    key="user_input",
)

# ---------------------------------------------------------------------------
# Prompt variation text areas (rendered side-by-side)
# ---------------------------------------------------------------------------
st.markdown("#### System Prompts")

prompt_cols = st.columns(num_prompts)
prompts: list[str] = []
for i, col in enumerate(prompt_cols):
    with col:
        p = st.text_area(
            f"Prompt {i + 1}",
            placeholder=f"System prompt {i + 1}…",
            height=175,
            key=f"prompt_{i}",
        )
        prompts.append(p)

st.divider()

# ---------------------------------------------------------------------------
# Run All button
# ---------------------------------------------------------------------------
run_clicked = st.button(
    "▶  Run All",
    type="primary",
    use_container_width=True,
    disabled=not user_input.strip(),
    help="Enter test input and at least 2 prompts to run.",
)

if run_clicked:
    active: list[tuple[int, str]] = [
        (i, p) for i, p in enumerate(prompts) if p.strip()
    ]

    if len(active) < 2:
        st.warning("Please fill in at least 2 prompt variations before running.")
        st.stop()

    results_map: dict[int, dict] = {}

    def _run_one(idx_prompt: tuple[int, str]) -> tuple[int, dict]:
        idx, prompt = idx_prompt
        try:
            raw = run_prompt(prompt, user_input, model=model, max_tokens=max_tokens)
            return idx, evaluate(raw)
        except Exception as exc:  # noqa: BLE001
            return idx, {"error": str(exc)}

    with st.spinner(f"Running {len(active)} prompt(s) in parallel…"):
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            futures = {pool.submit(_run_one, item): item[0] for item in active}
            for future in as_completed(futures):
                idx, result = future.result()
                results_map[idx] = result

    # Preserve insertion order for display
    ordered_prompts = [p for _, p in sorted(active)]
    ordered_results = [results_map[i] for i, _ in sorted(active)]

    st.session_state["prompts"] = ordered_prompts
    st.session_state["results"] = ordered_results
    st.session_state["run_input"] = user_input
    st.session_state["model"] = model

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------
if "results" in st.session_state:
    stored_prompts: list[str] = st.session_state["prompts"]
    stored_results: list[dict] = st.session_state["results"]
    stored_input: str = st.session_state["run_input"]
    stored_model: str = st.session_state["model"]

    st.subheader("Results")

    result_cols = st.columns(len(stored_results))
    for i, (col, result) in enumerate(zip(result_cols, stored_results)):
        with col:
            st.markdown(f"**Prompt {i + 1}**")

            if "error" in result:
                st.error(f"API error: {result['error']}")
                continue

            m1, m2, m3 = st.columns(3)
            m1.metric("Time (s)", f"{result['response_time']:.2f}")
            m2.metric("Words", result["word_count"])
            m3.metric("Tokens", result["output_tokens"])

            # Scrollable response container
            with st.container(height=320):
                st.markdown(result["response"])

    # -----------------------------------------------------------------------
    # Download report
    # -----------------------------------------------------------------------
    st.divider()

    valid_pairs = [
        (p, r)
        for p, r in zip(stored_prompts, stored_results)
        if "error" not in r
    ]

    if valid_pairs:
        report_md = generate_report(
            prompts=[p for p, _ in valid_pairs],
            results=[r for _, r in valid_pairs],
            user_input=stored_input,
            model=stored_model,
        )

        st.download_button(
            label="⬇  Download Comparison Report (.md)",
            data=report_md,
            file_name="prompt_lab_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
