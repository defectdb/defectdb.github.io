---
title: "Evaluation"
author: Maxim Menshikov
layout: defect
permalink: /expr/evaluation
group:
   - expr
---

Defects tied to how and when the parts of an expression are computed. When a result depends on assumptions the language does not guarantee — chiefly the relative order in which operands and side effects are evaluated — the program may work by accident on one toolchain and fail on another.

