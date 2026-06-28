---
title: "Misuse"
author: Maxim Menshikov
layout: defect
permalink: /gc/misuse
group:
   - gc
---

Patterns that overload the garbage collector by feeding it far more work than the program's logic requires. Allocation in tight loops, short-lived objects churned on a hot path, and structures that keep otherwise-dead memory reachable all force the collector to run more often and scan more, turning a transparent service into a measurable cost.
