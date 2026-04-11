"""Backward-compatible import wrapper."""

from app.services.modeling import providers as _providers
from app.services.modeling.providers import *  # noqa: F401,F403

# Preserve private names for existing tests/patches.
_resolve_model_path = _providers._resolve_model_path
_resolve_anomaly_model_dir = _providers._resolve_anomaly_model_dir
_load_anomaly_artifacts = _providers._load_anomaly_artifacts
_score_anomaly_record = _providers._score_anomaly_record
