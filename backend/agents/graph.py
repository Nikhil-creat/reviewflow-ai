"""LangGraph state machine:  sync -> next -> sentiment -> rag_voice -> dispatcher -> (vision) -> next ... -> END"""
from langgraph.graph import END, StateGraph

from .nodes import dispatch_node, next_node, rag_node, sentiment_node, sync_node, vision_node
from .state import AutopilotState


def _after_next(state) -> str:
    return "sentiment" if state.get("current") else END


def _after_dispatch(state) -> str:
    c = state["current"]
    a = state["analysis"]
    return "vision" if c["rating"] == 5 and a["sentiment"] == "positive" else "next"


def build_graph():
    g = StateGraph(AutopilotState)
    g.add_node("sync", sync_node)
    g.add_node("next", next_node)
    g.add_node("sentiment", sentiment_node)
    g.add_node("rag_voice", rag_node)
    g.add_node("dispatcher", dispatch_node)
    g.add_node("vision", vision_node)
    g.set_entry_point("sync")
    g.add_edge("sync", "next")
    g.add_conditional_edges("next", _after_next, {"sentiment": "sentiment", END: END})
    g.add_edge("sentiment", "rag_voice")
    g.add_edge("rag_voice", "dispatcher")
    g.add_conditional_edges("dispatcher", _after_dispatch, {"vision": "vision", "next": "next"})
    g.add_edge("vision", "next")
    return g.compile()


GRAPH = build_graph()
