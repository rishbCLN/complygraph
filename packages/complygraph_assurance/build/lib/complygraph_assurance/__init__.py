"""complygraph_assurance - infra-free Assurance Contract v1 export for ComplyGraph.

Keystone discovers the compliance pillar via this package's ``__version__``
(Assurance Contract v1 §7). The public API mirrors the CLI:

    from complygraph_assurance import (
        evaluate_compliance,   # run the real ComplyGraph control engine (infra-free)
        build_assurance_pack,  # -> Contract v1 proof-pack dict
        write_assurance,       # evaluate + write <out>/assurance.json
    )

Import stays light: only stdlib + this package are imported here. ComplyGraph's
control engine is located/imported lazily on first ``evaluate_compliance`` call.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .engine_bridge import (  # noqa: E402  (must follow __version__)
    EngineNotFoundError,
    EvaluationResult,
    InputError,
    available_frameworks,
    available_targets,
    evaluate_compliance,
)
from .builder import (  # noqa: E402
    CONTRACT_VERSION,
    build_assurance_pack,
    build_native_report,
    write_assurance,
)
from .cli import main  # noqa: E402

__all__ = [
    "__version__",
    "CONTRACT_VERSION",
    "evaluate_compliance",
    "available_frameworks",
    "available_targets",
    "build_assurance_pack",
    "build_native_report",
    "write_assurance",
    "EvaluationResult",
    "EngineNotFoundError",
    "InputError",
    "main",
]
