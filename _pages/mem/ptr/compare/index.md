---
title: "Comparison"
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/compare
group:
   - mem
   - ptr
---

Defects in how pointers are compared. The flagged pattern is comparing a pointer against a constant other than null, which is rarely meaningful: pointer values are assigned by the runtime and not fixed by the program, so such a test usually reflects a confusion between an address and the data it points to, or a null check written against the wrong literal.
