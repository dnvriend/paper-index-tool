"""OpenTelemetry integration for paper-index-tool.

This module provides observability (traces, metrics, logs) for the CLI.
Enable with --telemetry flag or OTEL_ENABLED=true environment variable.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""

from paper_index_tool.telemetry.config import ExporterType, TelemetryConfig
from paper_index_tool.telemetry.decorators import trace_span, traced
from paper_index_tool.telemetry.service import TelemetryService

__all__ = [
    "ExporterType",
    "TelemetryConfig",
    "TelemetryService",
    "traced",
    "trace_span",
]
