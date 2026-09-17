import json
import os
from typing import Any

import streamlit as st

# Headroom's anonymous metrics are not needed for this public demo.
os.environ.setdefault("HEADROOM_BEACON", "off")

from headroom import compress  # noqa: E402


def build_sample_payload() -> str:
    rows: list[dict[str, Any]] = []
    for index in range(80):
        row: dict[str, Any] = {
            "request_id": f"req-{index:04d}",
            "service": "checkout-api",
            "status": "ok",
            "region": "eu-west-1",
            "latency_ms": 118 + (index % 7),
            "message": "Request completed successfully",
        }
        if index == 17:
            row.update(
                status="error",
                latency_ms=2480,
                message="Payment provider timed out after three retries",
            )
        if index == 63:
            row.update(
                status="warning",
                latency_ms=910,
                message="Inventory response was slower than expected",
            )
        rows.append(row)

    return json.dumps(
        {
            "environment": "production",
            "generated_for": "Headroom Streamlit demo",
            "results": rows,
        },
        indent=2,
    )


def content_as_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False, indent=2)


st.set_page_config(
    page_title="Headroom Playground",
    page_icon="↘",
    layout="wide",
)

st.title("Headroom Playground")
st.caption(
    "Compress large JSON, logs and code before they reach an LLM. "
    "Everything in this demo runs inside the Streamlit app."
)

with st.sidebar:
    st.header("Compression settings")
    model = st.selectbox(
        "Target model",
        ["gpt-4o", "gpt-4.1", "claude-sonnet-4-5-20250929"],
        help="Used by Headroom for token counting and context-aware routing.",
    )
    target_ratio = st.slider(
        "Keep ratio",
        min_value=0.10,
        max_value=0.90,
        value=0.35,
        step=0.05,
        help="Lower values ask for more aggressive compression when supported.",
    )
    min_tokens = st.slider(
        "Minimum tokens",
        min_value=25,
        max_value=1000,
        value=100,
        step=25,
        help="Smaller inputs remain unchanged below this threshold.",
    )
    st.info(
        "This deployment uses Headroom's lightweight local compressors. "
        "The large ML prose model is disabled to keep the app fast and reliable."
    )

if "payload" not in st.session_state:
    st.session_state.payload = build_sample_payload()

button_left, button_right, spacer = st.columns([1, 1, 5])
with button_left:
    if st.button("Load sample", use_container_width=True):
        st.session_state.payload = build_sample_payload()
with button_right:
    if st.button("Clear", use_container_width=True):
        st.session_state.payload = ""

payload = st.text_area(
    "Content to compress",
    key="payload",
    height=420,
    placeholder="Paste JSON, logs, source code or another large tool output…",
)

if st.button("Compress with Headroom", type="primary", disabled=not payload.strip()):
    messages = [
        {
            "role": "user",
            "content": "Inspect this tool output and preserve errors, anomalies and useful context.",
        },
        {"role": "tool", "content": payload},
    ]

    try:
        with st.spinner("Compressing locally…"):
            compressed = compress(
                messages,
                model=model,
                protect_recent=0,
                target_ratio=target_ratio,
                min_tokens_to_compress=min_tokens,
                kompress_model="disabled",
            )

        st.session_state.compression_result = {
            "compressed": content_as_text(compressed.messages[-1]["content"]),
            "tokens_before": compressed.tokens_before,
            "tokens_after": compressed.tokens_after,
            "tokens_saved": compressed.tokens_saved,
            "ratio": compressed.compression_ratio,
            "transforms": compressed.transforms_applied,
            "original": payload,
        }
    except Exception as exc:  # Streamlit should surface packaging/runtime issues clearly.
        st.error(f"Compression failed: {exc}")

result = st.session_state.get("compression_result")
if result:
    st.divider()
    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Tokens before", f"{result['tokens_before']:,}")
    metric_b.metric("Tokens after", f"{result['tokens_after']:,}")
    metric_c.metric("Tokens saved", f"{result['tokens_saved']:,}")
    metric_d.metric("Reduction", f"{result['ratio']:.1%}")

    compressed_tab, original_tab, integration_tab = st.tabs(
        ["Compressed", "Original", "Python integration"]
    )
    with compressed_tab:
        st.code(result["compressed"], language="json", wrap_lines=True)
        st.download_button(
            "Download compressed output",
            data=result["compressed"],
            file_name="headroom-compressed.txt",
            mime="text/plain",
        )
        if result["transforms"]:
            st.caption("Transforms: " + ", ".join(result["transforms"]))
    with original_tab:
        st.code(result["original"], language="json", wrap_lines=True)
    with integration_tab:
        st.code(
            '''from headroom import compress

messages = [
    {"role": "user", "content": "Analyse these results"},
    {"role": "tool", "content": large_tool_output},
]

result = compress(
    messages,
    model="gpt-4o",
    protect_recent=0,
    kompress_model="disabled",
)

# Send result.messages to your OpenAI/Anthropic client.
print(result.tokens_saved)''',
            language="python",
        )

with st.expander("What this demo is showing"):
    st.markdown(
        "Headroom sits between an application and its language model. It reduces "
        "large, repetitive tool outputs while attempting to preserve errors, anomalies "
        "and boundaries. Savings vary by content: repetitive JSON and logs usually "
        "compress much more than short or already-dense prose."
    )

