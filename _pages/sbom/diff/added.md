---
title: "SBOM: package added"
author: Maxim Menshikov
layout: defect
permalink: /sbom/diff/added
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: sbom.diff
group:
   - sbom
   - diff
---
A dependency present in the current SBOM is missing from the previous snapshot

# Impact

When the current SBOM is compared against a previous snapshot (a baseline from
the last release, the main branch, or the prior build), this dependency appears
in the new SBOM but not in the old one — it was *added*. This is an
informational diff entry, not a fault in itself; its purpose is to draw a
reviewer's attention to a newly introduced component.

The practical significance:

- **New attack surface and new obligations.** Every added component brings its
  own code, its own potential vulnerabilities, and its own license terms into
  the product. An addition is the moment to evaluate those before they become a
  vulnerable-dependency or license-policy finding.
- **Visibility into supply-chain change.** Additions are frequently
  *transitive* — pulled in indirectly by bumping or adding a direct dependency —
  so a single intended change can quietly introduce several new packages. The
  diff makes that expansion visible.
- **Provenance check point.** A newly appearing name is the right place to catch
  typosquats, dependency-confusion substitutions, or an unexpected maintainer
  change, since the package is being introduced rather than merely carried over.

On its own the entry carries no defect; the consequences depend on what the added
package turns out to be, which downstream license and vulnerability checks then
assess.

# Vulnerability potential

A package addition is informational and has no direct security impact by itself —
adding a dependency is a normal, expected event and does not constitute a flaw.
It is flagged only so a human or policy can assess the new component.

The indirect relevance is that an addition is the *trigger point* for real
checks: a newly introduced package may carry a known-vulnerable version
(handled as a vulnerable-dependency finding) or an unexpected name that signals
a typosquat or dependency-confusion attack. Treat the entry as a prompt to run
vulnerability, license and provenance checks on the new component, not as a
vulnerability in its own right.

# Technical details

An SBOM diff is a set comparison between two bills of materials keyed by a stable
component identity — normally the package URL (purl) or `name@version`. With the
previous snapshot's component set `P` and the current set `C`, the *added* set is
`C \ P`: components present now but absent before. (The companion entries are
*removed* = `P \ C` and *bumped* = same name, different version.)

## Keying and granularity

The result depends on the key. Keying on `name` alone reports only first-time
package introductions; keying on `name@version` reports a version change as a
simultaneous remove+add unless the differ collapses those into a *bumped* entry.
A correct differ matches by name first, then classifies same-name pairs as
bumped and unmatched names as added/removed.

## Direct vs transitive

The added component may be a *direct* dependency the developer wrote into the
manifest, or a *transitive* one resolved by the package manager. Diffing the
fully resolved lockfile/SBOM (not just the manifest) surfaces transitive
additions that the manifest change does not mention. A single direct bump can
therefore produce many added entries.

## Snapshot baseline

The meaning of "added" is relative to whatever baseline was chosen. Comparing
against the last released SBOM answers "what is new since we shipped"; comparing
against the target branch answers "what does this PR introduce". The baseline
must be recorded for the diff to be interpretable.

# Catching the issue

Additions are surfaced by diffing SBOMs in the pipeline and reviewing the result
on every change.

## Diffing tooling

Generate an SBOM per build (Syft, CycloneDX tools, the build system's SBOM
output) and diff it against the stored baseline with `cyclonedx-cli diff`,
`syft ... diff`, `bom diff`, or GitHub's Dependency Review action, which
comments the dependency delta directly on pull requests. Commit lockfiles so the
resolved graph is reproducible and the diff is meaningful.

## Review and gating

Make the added-component list part of code review so a human evaluates each new
package's purpose, maintenance, popularity and provenance. Optionally gate new
*direct* additions behind an allow-list or an approval step, and automatically
run vulnerability and license scans on the added set so a risky introduction is
caught at the moment it enters rather than later. Dependency-pinning and
provenance checks (npm `--package-lock-only`, Sigstore/SLSA attestations) help
confirm the addition is the package you intended.

# How to reproduce

The "reproducer" is an SBOM diff, not runnable code. Below, the component
`left-pad` is present in the current SBOM but absent from the previous snapshot,
so the differ classifies it as *added*. Observe the component in `current` that
has no counterpart in `previous`.

```json
{
  "previous": {
    "components": [
      { "purl": "pkg:npm/express@4.18.2" },
      { "purl": "pkg:npm/lodash@4.17.21" }
    ]
  },
  "current": {
    "components": [
      { "purl": "pkg:npm/express@4.18.2" },
      { "purl": "pkg:npm/lodash@4.17.21" },
      { "purl": "pkg:npm/left-pad@1.3.0" }
    ]
  }
}
```

The resulting diff entry:

```yaml
sbom_diff:
  added:
    - name: left-pad
      version: 1.3.0
      purl: "pkg:npm/left-pad@1.3.0"
      scope: transitive       # pulled in by a bumped direct dependency
  removed: []
  bumped: []
```

