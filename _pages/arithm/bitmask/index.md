---
title: "Bitmasks"
author: Maxim Menshikov
layout: defect
permalink: /arithm/bitmask
group:
   - arithm
---

Defects in code that uses bitmasks to pack, test, or clear individual flags,
where the mask itself is wrong for the value it is applied to. The typical fault
is a mask whose set bits do not line up with the field being manipulated — a
stale constant, a wrong width, or an off-by-one shift — so the operation reads or
modifies bits the author never intended.

Because a masked `&`, `|`, or `&~` is always a legal expression, the compiler
offers no warning; the result is a silently incorrect flag set that misroutes
logic or corrupts a packed structure.

