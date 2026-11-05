# Agent Operating Rules

This document specifies mandatory operating rules and constraints for any AI agent working on this codebase.

---

## Rule 1: Maintain the Project Context File (`context.md`)
- **Primary Directive**: You must maintain a `context.md` file in the project root.
- The `context.md` file must be kept up-to-date with:
  1. Complete project context, architecture, tech stack, and module descriptions.
  2. Active Gemini model configurations, endpoints, and behaviors.
  3. Operating workflows and constraints.
- When adding features, changing workflows, or resolving bugs, review and update `context.md` accordingly.

---

## Rule 2: Clinical Safety and Medical Integrity
- **Never Hallucinate or Invent Information**: RxScribe is an assistance tool, not a prescriber.
- If handwriting is unreadable, ambiguous, or incomplete, transcribe it strictly as `"unclear"`. Never guess or fill in missing clinical fields.
- **Dictionary Suggestions Are Hints Only**: Never auto-apply suggestions to medicine names, dosages, or instructions.
- Ensure the disclaimer and human verification requirements are always visible in UI, JSON, and PDF outputs.

---

## Rule 3: Robust Gemini Vision Integration
- **Active Models Only**: Only use models actively supported by the Gemini API (e.g. `gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.8-flash`, `gemini-flash-latest`). Never revert to deprecated models like `gemini-2.5-flash` or `gemini-1.5-flash`.
- **Fault-Tolerant Fallback**: Always catch transient errors (such as 503 high demand or network drops) and fall back through alternative candidate models.
- **Transparent Diagnostics**: Report actionable error messages (differentiating between missing API keys, rate limits, busy models, and malformed inputs).

---

## Rule 4: Code Quality & Testing Rigor
- **Preserve Documentation**: Maintain existing comments, type annotations, and docstrings unless explicitly asked to modify them.
- **Verify All Changes**: Always run existing automated tests (`pytest`) and verify live or mock pipelines before declaring a task complete.
- **Zero Breaking Side Effects**: Ensure exports (JSON, PDF), fuzzy matching, and preprocessing preview interfaces remain functional across updates.
