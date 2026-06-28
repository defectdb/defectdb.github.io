---
title: "Licensing"
author: Maxim Menshikov
layout: defect
permalink: /sbom/license
group:
   - sbom
---

Defects where a dependency's license is incompatible with the policy governing the project that includes it — a copyleft obligation pulled into a codebase meant to stay permissive, a clause that forbids the intended distribution, or simply a license the organisation has not cleared for use. The code may work perfectly; the legal terms under which it ships do not.

These violations are easy to miss because a single transitive dependency, or a version bump that re-licenses a package, can introduce an unacceptable term without any visible change to first-party code, and the consequence — compliance exposure rather than a crash — surfaces only under review or audit.
