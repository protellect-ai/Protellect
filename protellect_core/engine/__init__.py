"""Hypothesis engine: precedent-based hypotheses for orphan GPCRs, with deterministic critique."""
from .io_parsers import parse_experiment, lookup_frame, InputError
from .engine import HypothesisEngine
from .cases import load_cases

__all__ = ["parse_experiment", "lookup_frame", "InputError", "HypothesisEngine", "load_cases"]
