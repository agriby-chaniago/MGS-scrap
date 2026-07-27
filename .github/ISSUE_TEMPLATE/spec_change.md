---
name: Spec change proposal
about: Propose a change to a normative part of MGS (specs/mgs/MGS-1.0.md)
labels: spec
---

**MGS is frozen at 1.0** (see `specs/mgs/MGS-1.0.md` §8/§9). Any change
to §5 (Requirements) — a new Requirement, a changed threshold, a
changed verdict condition — is a new spec version (1.1+), not an edit
to the existing document. This template is for proposing that, not for
requesting an immediate code change.

**What section of the spec does this affect?**

**What's the proposed change, and why?**

Please include the justification a new/changed threshold would need
(spec §5.3's Hamming-distance rationale is the model to match) — "it
seemed reasonable" isn't enough once a Requirement is normative.

**Does this need a new conformance fixture?**

Most spec changes do — see `conformance/` and `CONTRIBUTING.md`.

**Backward compatibility**

Would a Report evaluated against the current spec version still be
comparable after this change? If not, that's expected for a new spec
version, but should be stated explicitly (see `specs/mgs/MGS-1.0.md` §8).
