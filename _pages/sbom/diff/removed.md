---
title: "SBOM: package removed"
author: Maxim Menshikov
layout: defect
permalink: /sbom/diff/removed
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: sbom.diff
group:
   - sbom
   - diff
---
A dependency present in the previous SBOM is missing from the current one

# Impact

When the current SBOM is compared against a previous snapshot, this dependency
appears in the old SBOM but not in the new one — it was *removed*. Like the other
diff entries this is purely informational: a component left the dependency graph.
In most cases a removal is positive, because it shrinks the code that ships and
therefore the attack surface, the maintenance burden and the set of license
obligations.

What it is worth noticing:

- **Reduced surface, usually good.** Dropping a dependency removes its code,
  its potential CVEs and its license terms from the product. A removal often
  *resolves* prior vulnerable-dependency or license findings.
- **Possible loss of functionality or a vendored copy.** A package that
  disappears from the resolved graph might have been deliberately dropped, or it
  might have been replaced/vendored/inlined under a different name — in which
  case the code is still present but no longer tracked by the SBOM, which is the
  one mild downside to watch for.
- **Transitive ripple.** Removing or downgrading a direct dependency can drop
  several transitive packages at once; the diff makes that visible so the change
  is understood rather than assumed.

The entry itself reports no defect; it documents that the bill of materials got
smaller.

# Vulnerability potential

Removing a dependency has no direct security downside — it generally *reduces*
risk by eliminating code and any vulnerabilities or license obligations that came
with it, which is why both severity ratings are None.

The only security-relevant caveat is an indirect, low-likelihood one: if a
package "disappears" from the SBOM because it was vendored, statically inlined,
or renamed rather than genuinely deleted, the code may still run while no longer
being tracked by composition analysis — creating a blind spot where future
advisories against it would go unnoticed. That is a process/visibility concern to
verify, not a vulnerability introduced by the removal itself.

# Technical details

An SBOM diff is a set comparison between two bills of materials keyed by a stable
component identity (purl or `name@version`). With the previous component set `P`
and the current set `C`, the *removed* set is `P \ C`: components present in the
baseline but absent now. The complements are *added* = `C \ P` and *bumped* =
same name with a changed version.

## Keying and the remove/bump ambiguity

The classification hinges on the key. If the differ keys on `name@version`, a
version change looks like the old `name@old` being removed and `name@new` being
added; a correct differ first matches by `name`, reports matched-but-different
pairs as *bumped*, and only reports a name with no current match as truly
*removed*. Misconfigured keys are the main source of spurious "removed" noise.

## Direct vs transitive removal

A removal may be a *direct* dependency intentionally deleted from the manifest,
or a *transitive* one that fell out of the resolved graph because the package
that required it was itself removed, downgraded or restructured. Diffing the
resolved lockfile/SBOM rather than the manifest is what makes transitive
removals visible.

## Disappeared vs vendored

The SBOM only knows what its generator can see. A component can leave the SBOM
because it was genuinely dropped, or because it was copied into the tree
(vendored), bundled by a build step, or renamed — cases where the code persists
but its tracked identity does not. Distinguishing these requires looking at the
actual build output, not just the diff.

# Catching the issue

Removals are surfaced by the same SBOM-diff machinery used for additions and
bumps.

## Diffing tooling

Generate an SBOM per build (Syft, CycloneDX tools, native build SBOM output) and
diff it against the stored baseline with `cyclonedx-cli diff`, `syft ... diff`,
`bom diff`, or GitHub's Dependency Review action, which lists removed components
on the pull request. Commit lockfiles so the resolved graph — and therefore the
diff — is reproducible.

## Review focus

Because removals are generally benign, the review goal is mainly to confirm
intent: that the drop was deliberate and does not silently delete needed
functionality, and that a "removed" package was not merely vendored or renamed
into an untracked copy. Where a removal closes out a previously reported
vulnerable-dependency or license finding, link the two so the resolution is
recorded. Re-running vulnerability and license scans after the change confirms
the removal actually cleared the associated findings.

# How to reproduce

The "reproducer" is an SBOM diff, not runnable code. Below, `lodash` is present
in the previous snapshot but absent from the current SBOM, so the differ
classifies it as *removed*. Observe the component in `previous` with no
counterpart in `current`.

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
      { "purl": "pkg:npm/express@4.18.2" }
    ]
  }
}
```

The resulting diff entry:

```yaml
sbom_diff:
  added: []
  removed:
    - name: lodash
      version: 4.17.21
      purl: "pkg:npm/lodash@4.17.21"
      scope: transitive       # dropped when its requiring package was removed
  bumped: []
```

