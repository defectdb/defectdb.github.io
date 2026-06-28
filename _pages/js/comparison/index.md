---
title: "Comparison"
author: Maxim Menshikov
layout: defect
permalink: /js/comparison
group:
   - js
---

Defects arising from JavaScript's equality semantics, where loose `==` and `!=` coerce their operands before comparing. The conversion rules are intricate and unintuitive — `0`, `""`, `null`, and `undefined` compare equal in surprising combinations — so a comparison that looks correct can return the opposite of what was meant, which strict `===` would have caught.
