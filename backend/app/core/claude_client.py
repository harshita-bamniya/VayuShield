"""Compatibility shim — real implementation moved to llm_client.py."""

from app.core.llm_client import generate_text, get_groq_client as get_anthropic_client

__all__ = ["generate_text", "get_anthropic_client"]
