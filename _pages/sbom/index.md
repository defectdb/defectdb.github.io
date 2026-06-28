---
title: "SBOM"
author: Maxim Menshikov
layout: defect
permalink: /sbom
---

Defects in the software bill of materials — the inventory of third-party packages a project ships — and in the supply chain that fills it. These problems live not in the code an author wrote but in the dependencies they pulled in: a component carrying a known vulnerability, a license whose terms conflict with the project's policy, or an unreviewed change to the dependency set itself.

The risk here is that this surface is largely invisible at the source level and shifts with every build. A transitive dependency can introduce a CVE or an incompatible license without any change to first-party code, and an SBOM that drifts from one release to the next can add, drop, or re-version packages unnoticed. The entries group the standing hazards — known-vulnerable dependencies and license-policy violations — together with the differences that reveal when the inventory has moved.
