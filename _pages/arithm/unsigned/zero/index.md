---
title: "Related to zero"
author: Maxim Menshikov
layout: defect
permalink: /arithm/unsigned/zero
group:
   - arithm
   - unsigned
---

Defects in comparisons that relate an unsigned value to zero, where the test is
partially pointless because the type cannot represent the values the comparison
is checking for. A check such as `u < 0` is always false and `u >= 0` always
true, so the branch they guard is either dead or unconditionally taken, and the
intended bounds check quietly does nothing.

