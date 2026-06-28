---
title: "Order"
author: Maxim Menshikov
layout: defect
permalink: /expr/evaluation/order
group:
   - expr
   - evaluation
---

Defects where a value depends on the order in which subexpressions are evaluated, but that order is unspecified. Reading and modifying the same object within one expression, or relying on which argument runs first, makes the result a property of the compiler rather than the source — undefined or implementation-defined behaviour that shifts between builds and optimization levels.

