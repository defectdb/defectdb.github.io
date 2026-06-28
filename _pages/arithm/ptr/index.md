---
title: "Pointers"
author: Maxim Menshikov
layout: defect
permalink: /arithm/ptr
group:
   - arithm
---

Defects in pointer arithmetic, where an address is adjusted by an offset whose
derivation is unclear or unjustified. A magic increment, a hand-computed stride,
or an offset that ignores element size moves the pointer somewhere the author
cannot account for, and the resulting access reads or writes memory outside the
intended object.

The theme is arithmetic on addresses that is not tied to the layout it is
meant to traverse, which turns a small reasoning error into out-of-bounds
behaviour rather than a wrong-but-contained value.

