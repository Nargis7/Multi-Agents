import re
import time

import streamlit as st

from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

# ---------------------------------------------------------------- page setup
st.set_page_config(
    page_title="ResearchMind",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------- styling
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; max-width: 1150px; }
#MainMenu, footer { visibility: hidden; }

/* hero */
.hero {
    padding: 2.2rem 2rem;
    border-radius: 20px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
    color: #fff;
    box-shadow: 0 12px 40px rgba(99, 102, 241, 0.35);
    margin-bottom: 1.5rem;
}
.hero h1 { margin: 0; font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px; color: #fff; }
.hero p  { margin: .4rem 0 0; font-size: 1.05rem; opacity: .92; color: #fff; }

/* pipeline chips */
.chips { display: flex; gap: .6rem; flex-wrap: wrap; margin: .2rem 0 1.2rem; }
.chip {
    padding: .35rem .85rem; border-radius: 999px; font-size: .82rem; font-weight: 600;
    background: rgba(139, 92, 246, .14); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, .35);
}

/* metric cards */
.metric-card {
    padding: 1.1rem 1.2rem; border-radius: 16px;
    background: rgba(127, 127, 127, .08);
    border: 1px solid rgba(127, 127, 127, .2);
    text-align: center;
}
.metric-card .label { font-size: .78rem; text-transform: uppercase; letter-spacing: 1px; opacity: .65; }
.metric-card .value { font-size: 2rem; font-weight: 800; margin-top: .2rem; }

/* report card */
.report-card {
    padding: 1.6rem 1.8rem; border-radius: 16px;
    background: rgba(127, 127, 127, .06);
    border: 1px solid rgba(127, 127, 127, .2);
}

/* buttons */
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border: none; color: #fff; font-weight: 700;
    border-radius: 12px; padding: .65rem 1.4rem;
    transition: transform .15s ease, box-shadow .15s ease;
}
div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px); box-shadow: 0 8px 22px rgba(99, 102, 241, .45);
}
.stTextInput input { border-radius: 12px; padding: .75rem 1rem; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- helpers
EXAMPLES = [
    "Latest advances in federated learning",
    "Impact of AI on software engineering jobs",
    "How does retrieval-augmented generation work?",
    "State of quantum computing in 2026",
]


def set_topic(t: str):
    st.session_state.topic_input = t


def metric(label: str, value: str):
    st.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def parse_score(feedback: str) -> str:
    m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback)
    return f"{m.group(1)}/10" if m else "N/A"


def count_sources(text: str) -> int:
    return len(set(re.findall(r"https?://[^\s)\]>\"']+", text)))


def run_pipeline(topic: str) -> dict:
    """Same 4 steps as pipeline.py, but with live UI progress."""
    state = {}
    progress = st.progress(0, text="Starting…")

    with st.status("Running research pipeline…", expanded=True) as status:
        # step 1
        st.write("🔎 **Step 1** — Search agent is finding sources…")
        search_agent = build_search_agent()
        res = search_agent.invoke(
            {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]}
        )
        state["search_results"] = res["messages"][-1].content
        progress.progress(25, text="Search complete")

        # step 2
        st.write("📖 **Step 2** — Reader agent is scraping the best source…")
        reader_agent = build_reader_agent()
        res = reader_agent.invoke(
            {
                "messages": [
                    (
                        "user",
                        f"Based on the following search results about '{topic}', "
                        f"pick the most relevant URL and scrape it for deeper content.\n\n"
                        f"Search Results:\n{state['search_results'][:800]}",
                    )
                ]
            }
        )
        state["scraped_content"] = res["messages"][-1].content
        progress.progress(50, text="Scraping complete")

        # step 3
        st.write("✍️ **Step 3** — Writer is drafting the report…")
        research_combined = (
            f"SEARCH RESULTS : \n {state['search_results']} \n\n"
            f"DETAILED SCRAPED CONTENT : \n {state['scraped_content']}"
        )
        state["report"] = writer_chain.invoke({"topic": topic, "research": research_combined})
        progress.progress(75, text="Draft complete")

        # step 4
        st.write("🧐 **Step 4** — Critic is reviewing the report…")
        state["feedback"] = critic_chain.invoke({"report": state["report"]})
        progress.progress(100, text="Done")

        status.update(label="✅ Research complete", state="complete", expanded=False)

    time.sleep(0.4)
    progress.empty()
    return state


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🔎 ResearchMind")
    st.caption("A multi-agent research assistant")
    st.divider()

    st.markdown("**How it works**")
    st.markdown(
        "1. 🔎 **Search agent** finds sources via Tavily\n"
        "2. 📖 **Reader agent** scrapes the best page\n"
        "3. ✍️ **Writer** drafts a structured report\n"
        "4. 🧐 **Critic** scores and reviews it"
    )
    st.divider()

    st.markdown("**Try an example**")
    for ex in EXAMPLES:
        st.button(ex, key=f"ex_{ex}", on_click=set_topic, args=(ex,), use_container_width=True)

    st.divider()
    st.caption("Model: `llama3.2` via Ollama · make sure Ollama is running.")

# ---------------------------------------------------------------- hero
st.markdown(
    """
<div class="hero">
    <h1>🔎 ResearchMind</h1>
    <p>Enter any topic. Four AI agents will search, read, write and critique — end to end.</p>
</div>
<div class="chips">
    <span class="chip">Search</span><span class="chip">Read</span>
    <span class="chip">Write</span><span class="chip">Critique</span>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- input
if "topic_input" not in st.session_state:
    st.session_state.topic_input = ""

col_in, col_btn = st.columns([5, 1], vertical_alignment="bottom")
with col_in:
    topic = st.text_input(
        "Research topic",
        key="topic_input",
        placeholder="e.g. Latest advances in federated learning",
    )
with col_btn:
    run = st.button("Research →", type="primary", use_container_width=True)

if run:
    if not topic.strip():
        st.warning("Please enter a topic first.")
    else:
        try:
            st.session_state.result = run_pipeline(topic.strip())
            st.session_state.result_topic = topic.strip()
        except Exception as e:
            st.error(
                f"Something went wrong: {e}\n\n"
                "Check that Ollama is running, the `llama3.2` model is pulled, "
                "and your `TAVILY_API_KEY` is set in `.env`."
            )

# ---------------------------------------------------------------- results
result = st.session_state.get("result")
if result:
    st.markdown(f"### Results for: *{st.session_state.get('result_topic', '')}*")

    m1, m2, m3 = st.columns(3)
    with m1:
        metric("Critic score", parse_score(result["feedback"]))
    with m2:
        metric("Sources cited", str(count_sources(result["report"])))
    with m3:
        metric("Report length", f"{len(result['report'].split())} words")

    st.write("")
    tab_report, tab_critic, tab_search, tab_scrape = st.tabs(
        ["📄 Report", "🧐 Critic feedback", "🔎 Search results", "📖 Scraped content"]
    )

    with tab_report:
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown(result["report"])
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download report (.md)",
            data=result["report"],
            file_name="research_report.md",
            mime="text/markdown",
        )

    with tab_critic:
        st.markdown('<div class="report-card">', unsafe_allow_html=True)
        st.markdown(result["feedback"])
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_search:
        st.markdown(result["search_results"])

    with tab_scrape:
        st.markdown(result["scraped_content"])
else:
    st.info("👆 Enter a topic or pick an example from the sidebar to get started.")