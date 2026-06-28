---
title: "Division"
author: Maxim Menshikov
layout: defect
permalink: /arithm/division
group:
   - arithm
---

Defects in integer and floating-point division, where the divisor or the
operation itself is unsafe. The dominant case is a divisor that can reach zero,
which traps the process on most integer hardware and yields infinities or NaNs
in floating point — a reliable crash or a silently poisoned result depending on
the type.

The root cause is usually a divisor that is computed or read from input without
a prior check that it is non-zero, so the guard the operation needs is simply
missing on some path.

