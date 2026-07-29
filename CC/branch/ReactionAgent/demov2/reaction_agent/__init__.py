"""Reaction Analogy Agent — P0 contract freeze package.

P1-T1: re-exports build info for convenience. Canonical source remains
``reaction_agent.config``.
"""
from __future__ import annotations

from reaction_agent.config import BuildInfo, get_build_info

__all__ = ["BuildInfo", "get_build_info"]
