---
title: "Arithmetic"
author: Maxim Menshikov
layout: defect
permalink: /arithm
---

Defects that arise from numeric computation: where the value a program computes
diverges from the value the programmer intended, because the operation, the
operand, or the underlying machine representation behaves in a way the code did
not account for. This family spans the integer and floating-point domains, the
bit-level operators that treat numbers as raw patterns, and the pointer
arithmetic that reinterprets addresses as integers.

What unites these entries is that the symptom is rarely a syntax error or an
obvious crash at the offending line. A divisor reaches zero, a sum wraps past
its type's maximum, a shift exceeds the operand width, a float is compared for
exact equality, or an unsigned quantity is subtracted below zero — each produces
a result that is well-defined by the hardware yet wrong for the program, and the
damage usually surfaces far downstream as corrupted state, a bad branch, or a
security-relevant miscalculation.

