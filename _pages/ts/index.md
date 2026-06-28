---
title: "TypeScript"
author: Maxim Menshikov
layout: defect
permalink: /ts
---

Defects that arise when TypeScript's type system is bypassed rather than used. The compiler's guarantees hold only as far as the annotations are honest; every escape hatch that tells it to stop checking trades a compile-time error for a runtime one, quietly reintroducing the very class of bugs the types were meant to prevent.

The common theme is the deliberate suppression of a check the compiler was ready to perform. Reaching for `any`, asserting non-null, or otherwise overriding inference silences the diagnostic without changing the underlying value, so the unsoundness travels outward into code that trusted the type to be accurate.
