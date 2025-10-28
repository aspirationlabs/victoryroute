"""Turn predictor ADK package."""

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_AGENT_PATH = Path(__file__).with_name("agent.py")
_AGENT_SPEC = spec_from_file_location("turn_predictor_agent.agent", _AGENT_PATH)
if _AGENT_SPEC is None or _AGENT_SPEC.loader is None:  # pragma: no cover
    raise ImportError(f"Unable to load agent module from {_AGENT_PATH}")
agent = module_from_spec(_AGENT_SPEC)
_AGENT_SPEC.loader.exec_module(agent)
sys.modules["turn_predictor_agent.agent"] = agent

root_agent = agent.root_agent

__all__ = ["root_agent"]
