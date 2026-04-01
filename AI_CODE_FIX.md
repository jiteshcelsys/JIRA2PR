## File Structure

```
src/
  firewall/
    __init__.py
    firewall.py
    stages.py
    config.py
    metrics.py
    exceptions.py
  tests/
    firewall/
      __init__.py
      test_firewall.py
      test_stages.py
      test_metrics.py
      test_integration.py
      corpus/
        prompt_injection.json
        jailbreak.json
        benign.json
      conftest.py
docs/
  firewall/
    README.md
    CHANGELOG.md
```

---

### `src/firewall/exceptions.py`

```python
"""
Custom exceptions for the AI Firewall module.
"""


class FirewallError(Exception):
    """Base exception for all firewall-related errors."""
    pass


class FirewallConfigError(FirewallError):
    """Raised when firewall configuration is invalid."""
    pass


class FirewallStageError(FirewallError):
    """Raised when a firewall stage encounters an unrecoverable error."""

    def __init__(self, stage_name: str, message: str):
        self.stage_name = stage_name
        super().__init__(f"Stage '{stage_name}' error: {message}")


class FirewallBlockedError(FirewallError):
    """
    Raised (optionally) when content is blocked, for use in
    raise-on-block mode rather than returning a FirewallResult.
    """

    def __init__(self, reason: str, stage: str, score: float):
        self.reason = reason
        self.stage = stage
        self.score = score
        super().__init__(f"Content blocked by stage '{stage}': {reason} (score={score:.3f})")
```

---

### `src/firewall/config.py`

```python
"""
Configuration dataclasses for the AI Firewall and its stages.

All fields use sane defaults so callers only need to override
what they care about.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class FirewallMode(str, Enum):
    """Controls what the firewall does when content is blocked."""
    RETURN_RESULT = "return_result"   # Return FirewallResult with blocked=True
    RAISE_EXCEPTION = "raise_exception"  # Raise FirewallBlockedError


class StageAction(str, Enum):
    """Action to take when a stage flags content."""
    BLOCK = "block"          # Stop pipeline, mark as blocked
    WARN = "warn"            # Continue pipeline, add warning
    LOG_ONLY = "log_only"    # Continue pipeline, log only


@dataclass
class RegexStageConfig:
    """Config for the regex-based pattern matching stage."""
    enabled: bool = True
    action: StageAction = StageAction.BLOCK
    # Additional patterns can be injected per API node
    extra_patterns: List[str] = field(default_factory=list)
    # Override the full pattern list (disables built-ins if set)
    override_patterns: Optional[List[str]] = None


@dataclass
class LLMJudgeStageConfig:
    """Config for the LLM-as-judge stage."""
    enabled: bool = True
    action: StageAction = StageAction.BLOCK
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 10
    # Score threshold above which content is considered malicious
    block_threshold: float = 0.75
    # API key resolved from env if not provided directly
    api_key: Optional[str] = None
    timeout_seconds: float = 10.0


@dataclass
class NeMoColangStageConfig:
    """Config for the NeMo Guardrails / Colang-based stage."""
    enabled: bool = False   # Requires NeMo Guardrails installed
    action: StageAction = StageAction.BLOCK
    colang_config_path: Optional[str] = None
    block_threshold: float = 0.80


@dataclass
class SemanticSimilarityStageConfig:
    """Config for the semantic similarity stage against known-bad embeddings."""
    enabled: bool = True
    action: StageAction = StageAction.BLOCK
    model: str = "text-embedding-3-small"
    block_threshold: float = 0.90
    api_key: Optional[str] = None
    timeout_seconds: float = 10.0


@dataclass
class FirewallConfig:
    """
    Top-level firewall configuration.

    Example usage::

        config = FirewallConfig(
            mode=FirewallMode.RAISE_EXCEPTION,
            llm_judge=LLMJudgeStageConfig(block_threshold=0.8),
        )
        fw = AIFirewall(config=config)
    """
    mode: FirewallMode = FirewallMode.RETURN_RESULT

    # Stage configs
    regex: RegexStageConfig = field(default_factory=RegexStageConfig)
    llm_judge: LLMJudgeStageConfig = field(default_factory=LLMJudgeStageConfig)
    nemo_colang: NeMoColangStageConfig = field(default_factory=NeMoColangStageConfig)
    semantic_similarity: SemanticSimilarityStageConfig = field(
        default_factory=SemanticSimilarityStageConfig
    )

    # If True, all stages run even after a BLOCK; useful for metric collection
    run_all_stages_for_metrics: bool = False

    # Feature flag – master switch
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "FirewallConfig":
        """
        Build a config from environment variables.

        Supported env vars:
          FIREWALL_ENABLED          = "true" / "false"
          FIREWALL_MODE             = "return_result" / "raise_exception"
          FIREWALL_LLM_MODEL        = e.g. "gpt-4o-mini"
          FIREWALL_LLM_THRESHOLD    = float, default 0.75
          FIREWALL_OPENAI_API_KEY   = OpenAI API key
          FIREWALL_RUN_ALL_STAGES   = "true" / "false"
        """
        def _bool(key: str, default: bool) -> bool:
            val = os.getenv(key, "").lower()
            if val == "true":
                return True
            if val == "false":
                return False
            return default

        def _float(key: str, default: float) -> float:
            try:
                return float(os.environ[key])
            except (KeyError, ValueError):
                return default

        api_key = os.getenv("FIREWALL_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

        return cls(
            enabled=_bool("FIREWALL_ENABLED", True),
            mode=FirewallMode(os.getenv("FIREWALL_MODE", FirewallMode.RETURN_RESULT.value)),
            run_all_stages_for_metrics=_bool("FIREWALL_RUN_ALL_STAGES", False),
            llm_judge=LLMJudgeStageConfig(
                model=os.getenv("FIREWALL_LLM_MODEL", "gpt-4o-mini"),
                block_threshold=_float("FIREWALL_LLM_THRESHOLD", 0.75),
                api_key=api_key,
            ),
            semantic_similarity=SemanticSimilarityStageConfig(
                api_key=api_key,
            ),
        )
```

---

### `src/firewall/metrics.py`

```python
"""
Metrics collection and reporting