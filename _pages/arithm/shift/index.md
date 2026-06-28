---
title: "Bit shift"
author: Maxim Menshikov
layout: defect
permalink: /arithm/shift
group:
   - arithm
---

Defects in bit-shift operations, where the shift is incorrect for the operand it
is applied to. The common faults are a shift count that meets or exceeds the
type's width — which is undefined on many platforms — and shifting a signed
value so that bits move into or out of the sign position, changing the value's
meaning rather than just its magnitude.

Because the operators accept any count and any operand type, the mistake
compiles cleanly and yields a platform-dependent or sign-corrupted result.

