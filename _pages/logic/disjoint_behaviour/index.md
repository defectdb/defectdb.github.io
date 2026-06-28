---
title: "Disjoint behaviours"
author: Maxim Menshikov
layout: defect
permalink: /logic/disjoint_behaviour
group:
   - logic
---

Defects where behaviours declared to be mutually exclusive turn out to overlap. When observed behaviour matches more than one of a set meant to be disjoint, the cases are not the clean partition the specification assumed — guards are ambiguous, and which branch governs becomes undefined or order-dependent.

