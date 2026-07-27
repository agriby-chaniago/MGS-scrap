"""modelgate — reference implementation of MGS (Model Gate Specification).

Public API surface (stable once tagged 1.0, see ROADMAP.md Fase 4 / D5.1):
    modelgate.audit, modelgate.Manifest, modelgate.Report

Everything else under `modelgate._internal` (once it exists) may change
without notice between minor versions. This package is currently a
Fase 1 packaging skeleton — the Reader/Manifest/Checker/Report pipeline
itself is built in Fase 2 (see ../../../ROADMAP.md).
"""

__version__ = "0.0.0.dev0"
