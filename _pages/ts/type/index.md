---
title: "Types"
author: Maxim Menshikov
layout: defect
permalink: /ts/type
group:
   - ts
---

Defects from annotations that opt out of type checking instead of describing the data. Using `any` disables all checking for a value and lets unsound assumptions spread to everything it touches, while a non-null assertion (`!`) promises the compiler a value is present without proof — so when it is in fact `null` or `undefined`, the guard that should have caught it is gone and the failure moves to runtime.
