---
title: "Fractional part"
author: Maxim Menshikov
layout: defect
permalink: /arithm/float/fractional_part
group:
   - arithm
   - float
---

Defects where code assumes a floating-point value carries a meaningful
fractional part that is in fact absent. Integer division feeding a float, an
earlier truncation, or a value that was always whole leaves nothing after the
decimal point, so logic that depends on that fraction — a remainder, a
sub-unit quantity, an interpolation weight — operates on zero and quietly
produces the wrong answer.

