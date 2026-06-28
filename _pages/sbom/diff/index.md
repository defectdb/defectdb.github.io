---
title: "Diff"
author: Maxim Menshikov
layout: defect
permalink: /sbom/diff
group:
   - sbom
---

Changes between two software bills of materials — what entered, left, or moved in a project's dependency set from one build or release to the next. A diff is not itself a fault, but it is where supply-chain risk first becomes visible, and an unexplained change is a defect waiting to be examined.

The cases cover a package that appears where it was not before, one that vanishes, and one whose pinned version shifts. Each can silently alter the vulnerability, license, and behaviour profile of a release, which is why the movement is worth flagging in its own right.
