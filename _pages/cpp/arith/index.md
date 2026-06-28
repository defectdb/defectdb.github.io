---
title: "Arithmetic"
author: Maxim Menshikov
layout: defect
permalink: /cpp/arith
group:
   - cpp
---

Arithmetic that goes wrong because of how C++ sizes and promotes its operands rather than because of the math itself. The classic trap is an expression evaluated in a narrow type — where overflow or truncation has already happened — and only then assigned or widened into a larger type, so the wider result faithfully preserves a value that was already corrupted.
