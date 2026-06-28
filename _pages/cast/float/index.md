---
title: "Floating point numbers"
author: Maxim Menshikov
layout: defect
permalink: /cast/float
group:
   - cast
---

Conversions involving floating-point numbers, where moving to or from a real type drops information without warning. The characteristic case is an implicit float-to-integer conversion that truncates the fractional part toward zero — and produces undefined behaviour when the value is too large for the target — turning a deliberate-looking computation into a silent loss of precision.
