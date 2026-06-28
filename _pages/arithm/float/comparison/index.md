---
title: "Comparison"
author: Maxim Menshikov
layout: defect
permalink: /arithm/float/comparison
group:
   - arithm
   - float
---

Defects from comparing floating-point values for exact equality, where two
results that are mathematically equal differ in their last bits because of
accumulated rounding. An `==` or `!=` test on such values succeeds or fails
unpredictably, so the correct approach is a tolerance comparison against an
appropriate epsilon rather than bit-exact equality.

