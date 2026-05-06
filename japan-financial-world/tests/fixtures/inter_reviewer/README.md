# Inter-reviewer reproducibility fixtures (v1.23.2 placeholder)

This directory ships the **format placeholder** for v1.23.2
Validation Category 5 — *inter-reviewer reproducibility*.

## What this is

A small, scaffolded format for capturing reviewer notes on a
single ``StressFieldReadout`` audit. v1.23.2 cannot pin
inter-reviewer reproducibility with humans (no reviewer panel
exists) — it pins only that the format is parseable and that
its fields are jurisdiction-neutral.

## What this is **NOT**

- No human reviewer ever signed any of these notes.
- No claim about real-world reviewer agreement is encoded.
- No claim about the readout under review is encoded — these
  are reviewer-side notes, not v1.21.3 readout content.
- The schema carries no v1.21.0a / v1.22.0 boundary-forbidden
  field. The v1.23.2 forbidden-name boundary applies to
  reviewer notes too — see ``world/forbidden_tokens.py`` for
  the full list.

## Schema (parseable subset)

A reviewer note is a JSON / YAML object with at least the
following top-level keys:

```yaml
note_id: "reviewer_note:placeholder:v1_23_2:01"
readout_id: "stress_field_readout:<stress_program_application_id>"
reviewer_kind: "human"          # closed set: {"human"}; v1.23.2 placeholder only
reasoning_mode: "human_authored" # closed set: {"human_authored"}; v1.23.2 placeholder only
notes: "free-form text — descriptive only, no outcome / forecast claim"
```

Future v1.x milestones (or external research collaborations)
will populate this directory with actual reviewer notes once
a reviewer panel exists. v1.23.2 only pins the schema's
shape, the closed-set ``reviewer_kind`` /
``reasoning_mode`` discipline, and the absence of forbidden
tokens in the schema text.

## v1.24+ note

The companion v1.24 candidate — **manual_annotation
interaction layer** — will consume this format. v1.23.2 ships
the format only; v1.24 adds the runtime annotation layer.
