---
title: "License policy violation"
author: Maxim Menshikov
layout: defect
permalink: /sbom/license/violation
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: sbom.license
group:
   - sbom
   - license
---
The package's declared license fails the configured license policy

# Impact

A dependency in the software bill of materials carries a declared license whose
terms violate the organization's configured license policy. Typical policies
forbid strong-copyleft licenses (GPL-2.0/3.0, AGPL-3.0) in proprietary or
SaaS products, disallow non-OSI / "source-available" or non-commercial licenses
(BSL, SSPL, Elastic License, JSON "good, not evil"), reject packages with no
declared license at all, or require that every component sit on an approved
allow-list.

The consequences are primarily legal, commercial and operational:

- **License obligations are triggered unknowingly.** Copyleft terms can require
  that derivative works — potentially the company's own proprietary code linked
  against the dependency — be distributed under the same license, i.e. with
  source disclosure. AGPL extends this to software merely *offered over a
  network*, which catches SaaS deployments that never "distribute" a binary.
- **Distribution and shipping risk.** A release that bundles a policy-violating
  component may have to be pulled, re-architected to remove the dependency, or
  relicensed; downstream redistribution and OEM agreements can be breached.
- **Audit and acquisition exposure.** License non-compliance surfaces in M&A due
  diligence and customer security/compliance reviews, and can block deals or
  trigger contractual penalties and remediation costs.
- **Attribution / notice failures.** Even permissive licenses (MIT, BSD,
  Apache-2.0) impose attribution and NOTICE-file obligations; failing to meet
  them is itself a policy violation in many configurations.

# Vulnerability potential

A license-policy violation is fundamentally a legal and compliance defect, not a
memory-safety or code-execution bug, so its direct security impact is limited.
It does not by itself cause memory corruption, injection or privilege
escalation, which is why the vulnerability rating here is low.

There are, however, secondary security-adjacent signals worth noting:

1. **Provenance / supply-chain signal.** A missing, ambiguous or unexpected
   license often indicates a package of poor provenance — an unmaintained fork,
   a vendored copy, or a typosquat — which correlates with weaker security
   hygiene and a higher chance of accompanying vulnerabilities.
2. **Forced source disclosure as information exposure.** Where a strong-copyleft
   obligation is triggered, complying may require publishing proprietary source
   that the organization considered confidential; that is an information-exposure
   consequence, albeit a contractual/business one rather than an exploit.

These are reasons to treat the finding seriously, but they are governance
concerns; if the security posture of the dependency itself is in question,
that is tracked separately as a vulnerable-dependency finding.

# Technical details

License checking compares each component's declared license against a policy.
The component's license is read from package metadata and normalized to an
[SPDX license identifier](https://spdx.org/licenses/) (e.g. `MIT`,
`Apache-2.0`, `GPL-3.0-or-later`), including SPDX expressions such as
`(MIT OR Apache-2.0)` or `GPL-2.0-only WITH Classpath-exception-2.0`. The
policy engine then evaluates each identifier against allow/deny lists or
category rules and raises a violation on a deny match, an unknown/`NOASSERTION`
license, or a license absent from the allow-list under a default-deny policy.

## Where the license comes from

Sources vary by ecosystem and are not always reliable: the `license`/`licenses`
field in `package.json`, the `License`/`Classifier` fields in Python metadata,
`<licenses>` in a Maven POM, the `license` key in `Cargo.toml`, Go module
headers, or a `LICENSE`/`COPYING` text file scanned heuristically (e.g. by
ScanCode/Licensee) when no machine-readable field exists. Mismatches between the
declared field and the actual license text are common and are themselves a
finding.

## Copyleft and linkage nuance

The severity of a copyleft obligation depends on how the dependency is combined:
static vs dynamic linking, aggregation vs derivative work, and distribution vs
network use. LGPL permits dynamic linking from proprietary code under
conditions; GPL generally does not for a combined work; AGPL's network clause
removes the "no distribution, no obligation" escape hatch. A correct policy
therefore considers not just the SPDX id but the linkage and deployment context,
which is why some violations are configuration-specific.

## Transitive dependencies

The violating component is frequently a transitive dependency several levels
deep, pulled in indirectly, so the offending license never appears in the
project's own manifest and is only visible once the full dependency tree is
resolved into the SBOM.

# Catching the issue

License compliance is enforced by generating an SBOM and gating on it in CI so
that no policy-violating component reaches a release.

## SBOM generation

Produce a complete, transitive SBOM in a standard format —
[CycloneDX](https://cyclonedx.org/) or [SPDX](https://spdx.dev/) — with tools
such as Syft, `cyclonedx-cli`/language plugins, or the build system's own SBOM
output. Ensure license fields are populated, falling back to text scanning
(ScanCode, Licensee, FOSSA, ScanOSS) where metadata is missing.

## Policy gates

Run a policy engine over the SBOM in the pipeline: Grype/`syft` with a license
ruleset, OSS Review Toolkit (ORT), FOSSA, Snyk License Compliance,
WhiteSource/Mend, `pip-licenses`/`license-checker` for single ecosystems, or a
custom check that fails the build on a deny-list match or an unknown license.
Configure the policy as default-deny with an explicit allow-list for the
strongest guarantee.

## Process controls

Maintain an approved-license allow-list and an exception register; require a
reviewed approval before any new license category enters the product. Generate
and ship the attribution / NOTICE file automatically so permissive-license
obligations are met. Re-run the gate on every dependency change, since a
transitive bump can silently introduce a new license.

# How to reproduce

The "reproducer" is an SBOM fragment, not runnable code. Below is a CycloneDX
excerpt for a proprietary product whose policy is *allow `MIT`, `Apache-2.0`,
`BSD-3-Clause`; deny all copyleft*. The `chatty-logger` component declares
`GPL-3.0-only`, which the policy denies — observe the license id against the
deny rule.

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "components": [
    {
      "type": "library",
      "name": "tiny-utils",
      "version": "1.4.2",
      "purl": "pkg:npm/tiny-utils@1.4.2",
      "licenses": [{ "license": { "id": "MIT" } }]
    },
    {
      "type": "library",
      "name": "chatty-logger",
      "version": "0.9.0",
      "purl": "pkg:npm/chatty-logger@0.9.0",
      "licenses": [{ "license": { "id": "GPL-3.0-only" } }]
    }
  ]
}
```

The same situation expressed as a manifest, where the transitive pull is the
real source of the violation:

```yaml
# package policy: deny copyleft (GPL/AGPL/LGPL), deny NOASSERTION
dependencies:
  - name: chatty-logger      # declared license: GPL-3.0-only  -> POLICY VIOLATION
    version: 0.9.0
    direct: false            # pulled in transitively via "report-kit"
  - name: mystery-lib        # declared license: NOASSERTION    -> POLICY VIOLATION
    version: 2.0.0
    direct: true
```

