---
title: "Unsigned"
author: Maxim Menshikov
layout: defect
permalink: /arithm/unsigned
group:
   - arithm
---

Defects that stem from the wraparound semantics of unsigned types, where a value
can never be negative and crossing below zero instead jumps to a very large
number. Subtracting one unsigned quantity from a larger one, or reasoning about
unsigned values as if they shared the ordering of signed integers, is the
recurring trap.

The most insidious form involves comparisons against zero: a test that would be
meaningful for a signed value becomes partially or wholly pointless once the
operand is unsigned, since the impossible cases are silently unreachable and the
guard they were meant to provide never fires.

