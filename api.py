"""
Backend for the React UI. Wraps your existing agents.py and streams progress.
Run:  uvicorn api:app --reload --port 8000
Ollama is only used here (through agents.py). The browser never talks to it.
"""
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

app = FastAPI(title="Relay API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


def _text(msg) -> str:
    c = msg.content
    if isinstance(c, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in c)
    return c


def _event(**payload) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/research")
def research(req: ResearchRequest):
    topic = req.topic.strip()

    def stream():
        try:
            # 1 - search
            yield _event(type="step", step=1)
            res = build_search_agent().invoke(
                {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]}
            )
            search_results = _text(res["messages"][-1])

            # 2 - read
            yield _event(type="step", step=2)
            res = build_reader_agent().invoke(
                {
                    "messages": [
                        (
                            "user",
                            f"Based on the following search results about '{topic}', "
                            f"pick the most relevant URL and scrape it for deeper content.\n\n"
                            f"Search Results:\n{search_results[:800]}",
                        )
                    ]
                }
            )
            scraped = _text(res["messages"][-1])

            # 3 - write
            yield _event(type="step", step=3)
            research = (
                f"SEARCH RESULTS : \n {search_results} \n\n"
                f"DETAILED SCRAPED CONTENT : \n {scraped}"
            )
            report = writer_chain.invoke({"topic": topic, "research": research})

            # 4 - critique
            yield _event(type="step", step=4)
            feedback = critic_chain.invoke({"report": report})

            yield _event(
                type="result",
                data={
                    "search_results": search_results,
                    "scraped_content": scraped,
                    "report": report,
                    "feedback": feedback,
                },
            )
        except Exception as e:  # surface the real error in the UI
            yield _event(type="error", message=str(e))

    return StreamingResponse(stream(), media_type="text/event-stream")