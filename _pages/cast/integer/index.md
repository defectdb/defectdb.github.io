---
title: "Integers"
author: Maxim Menshikov
layout: defect
permalink: /cast/integer
group:
   - cast
---

Conversions between integer types that do not preserve the original value. The dominant case is implicit truncation, where a wider integer is assigned into a narrower one and the high-order bits are discarded — flipping magnitude or sign whenever the value exceeds the destination's range, with no diagnostic from the compiler.
