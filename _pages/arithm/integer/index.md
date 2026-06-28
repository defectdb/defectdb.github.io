---
title: "Integers"
author: Maxim Menshikov
layout: defect
permalink: /arithm/integer
group:
   - arithm
---

Defects in integer arithmetic, where a computed value exceeds the range its type
can hold. The central case is overflow: a sum, product, or accumulation that
grows past the type's maximum wraps around to a small or negative value instead
of failing, and that wrapped result then flows into sizes, indices, or
allocation lengths.

Because the wrap is silent and deterministic, the bug is invisible until the
operands grow large enough to trigger it, at which point it manifests as
corrupted state or an exploitable size miscalculation.

