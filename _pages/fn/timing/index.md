---
title: "Timing"
author: Maxim Menshikov
layout: defect
permalink: /fn/timing
group:
   - fn
---

Defects in the temporal contract of a call: how long it may run and what
happens when it does not return promptly. Invoking an operation that can block
indefinitely — a network exchange, a lock, an external request — without a
timeout leaves the program at the mercy of a dependency that may never respond,
turning a slow peer into an unbounded hang.

