---
title: "Expressions"
author: Maxim Menshikov
layout: defect
permalink: /expr
---

Defects in how expressions are evaluated and qualified, rather than in the operators they are built from. The concern here is the semantics layered on top of syntax: when the language computes the parts of an expression, and what type qualifiers promise about the values flowing through it.

These problems are easy to overlook because the code reads correctly left to right. Reliance on an unspecified order of evaluation, or quietly stripping a qualifier such as `const`, leaves source that looks reasonable yet behaves differently across compilers or breaks a guarantee the type system was meant to enforce.

