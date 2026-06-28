---
title: "Floating point numbers"
author: Maxim Menshikov
layout: defect
permalink: /arithm/float
group:
   - arithm
---

Defects rooted in the nature of floating-point representation, where values are
binary approximations rather than the exact decimals they appear to be. Code
that treats a `float` or `double` as if it held a precise number eventually
trips over rounding error, and the two recurring forms of that mistake are
testing such values for exact equality and assuming a fractional component is
present when rounding or truncation has already discarded it.

