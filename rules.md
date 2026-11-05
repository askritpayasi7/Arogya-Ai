# Project Rules & Development Guidelines

Welcome to the **Research-Backed Health & FSSAI Advisory Application** repository. All human developers and AI assistants working on this codebase must adhere strictly to these rules.

---

## Rule 1: Mandatory Context Continuity via `progress.md` (STRICT)

1. **Persistent State Logging**:
   - A file named `progress.md` must ALWAYS exist in the root of this repository.
   - Every AI agent and human contributor **MUST update `progress.md`** upon completing any task, subtask, or architectural pivot.
   - `progress.md` must contain:
     - The current high-level architecture overview and active tech stack.
     - An up-to-date roadmap and milestone status.
     - Detailed changelog of files modified, added, or deleted with explicit rationale.
     - Known issues, technical debt, or blocked items.
     - Concrete, numbered "Immediate Next Steps" so that **any subsequent AI session or developer can immediately pick up context with zero information loss**.
2. **Pre-Task Context Check**:
   - Before executing code changes or new features, every AI assistant must read `progress.md` to align with the current operational state.

---

## Rule 2: Evidence Grounding & Citation Integrity

1. **No Hallucinated Health Claims**:
   - Every health advice, nutritional limit, additive evaluation, or dietary claim generated or supported by this application must be strictly grounded in:
     - **Peer-reviewed scientific research papers** (e.g. PubMed/PMC, Lancet, ICMR-NIN).
     - **FSSAI statutory regulations and standards** (Food Safety and Standards Act, Food Safety and Standards Regulations, Gazette notifications).
2. **Mandatory Provenance**:
   - Any retrieval or answer synthesized by the system must include verifiable citations:
     - Document title / regulation clause.
     - Author(s) and publication year (for research papers) or Gazette/Notification number (for FSSAI).
     - Exact snippet or chunk reference.

---

## Rule 3: Python Engineering Standards

1. **Modular Architecture**:
   - Keep business logic decoupled: ingestion, vector storage, retrieval, synthesis, and presentation (terminal runner / future CLI) must reside in distinct modules.
2. **Type Safety & Data Validation**:
   - Use Python standard type hints (`typing`) across all signatures.
   - Use Pydantic models for configuration, document metadata, and query responses.
3. **Robust External Integrations**:
   - Integrations with external services (such as Ollama or ChromaDB) must fail gracefully with descriptive error messages and troubleshooting hints (e.g., verifying `ollama serve` and model availability).
   - Mock/offline fallbacks must be available for testing environments.

---

## Rule 4: Verification and Testing

1. **Automated Test Coverage**:
   - Every new feature, loader, or database module must be accompanied by unit tests in the `tests/` directory.
   - Tests must pass cleanly (`pytest`) before any milestone is marked complete in `progress.md`.
2. **Terminal First, CLI Later**:
   - Work currently proceeds via executable terminal scripts (`python -m health_app.terminal_runner ...`).
   - Rich CLI frameworks (Click/Typer) will be introduced in subsequent milestones without breaking underlying core libraries.
