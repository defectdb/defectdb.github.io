---
title: "Casts"
author: Maxim Menshikov
layout: defect
permalink: /cast
---

Defects introduced when a value is converted from one type to another and the new type cannot faithfully represent the old one. Casts — especially the implicit conversions a compiler inserts without comment — quietly change a value's range, precision, or meaning, so the bug lives at the type boundary rather than in any single expression.

The entries group by what is being reinterpreted: real numbers losing their fractional part on the way to an integer, integers being narrowed into a type too small to hold them, and pointers being squeezed into integers that may not be wide enough to round-trip an address. Each is a place where information silently disappears or an assumption about width and signedness is broken.
