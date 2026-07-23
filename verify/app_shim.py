"""Test-only shim: works around the invalid Chroma collection name 'kb'
(1-char short of Chroma's 3-char minimum) WITHOUT touching app code.
Everything else runs the real app unmodified."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from agents import rag_agent  # noqa: E402

rag_agent.COLLECTION = "kbverify"  # valid per Chroma naming rules

from main import app  # noqa: E402,F401
