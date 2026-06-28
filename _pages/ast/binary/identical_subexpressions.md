---
title: "Identical subexpressions in binary operation"
author: Maxim Menshikov
layout: defect
permalink: /ast/binary/identical_subexpressions
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: ast.binary
group:
   - ast
   - binary
---
The corresponding operation doesn't encourage the use of identical subexpressions

# Impact

A binary operator whose left and right operands are syntactically identical is
almost always a mistake. Many such expressions are *degenerate*: ``x && x`` and
``x || x`` reduce to ``x``, ``x == x`` is always true, ``x != x`` always false,
``x - x`` is zero, and ``x & x`` / ``x | x`` are just ``x``. The author surely
meant one of the operands to be a *different* variable — a neighbouring field, the
next array element, the other endpoint of a range. The visible effect is a check
or computation that quietly collapses to a constant or to a single operand, so a
condition that was supposed to compare two things instead tests nothing, and a
formula that was supposed to combine two quantities returns a trivial value. The
intended logic is simply missing.

# Vulnerability potential

The security impact follows from what the collapsed expression was guarding.

1. If a range or bounds check degenerates — e.g. ``if (lo <= x && lo <= y)``
   written as ``if (lo <= x && lo <= x)`` — one half of the validation is gone,
   and an out-of-range value on the unchecked variable slips through into a buffer
   index or allocation size.
2. A comparison that was meant to detect a mismatch (two hashes, two lengths, two
   pointers) but compares one value with itself always reports "equal", defeating
   an integrity or authentication check.

Most occurrences are harmless logic typos, so severity is low in general, but the
guarding cases can be serious.

# Technical details

The defect is defined at the abstract-syntax-tree level: a ``BinaryOperator``
node whose two child subtrees are structurally equal. A checker compares the two
operand ASTs and reports a match for operators where identical operands are
meaningless or degenerate (relational, equality, logical-and/or, subtraction,
bitwise xor/and/or, division, modulo). The usual root cause is *copy-paste*: a
sub-expression is duplicated and the editor forgets to change one of the copies.

## Operators worth distinguishing
- ``==``/``!=``/``<=``/``>=`` on identical operands: constant truth value — likely
  a wrong operand.
- ``-``/``^``/``%``: always zero — almost certainly a typo.
- ``&&``/``||``/``&``/``|``: redundant — the duplicate adds nothing.
- ``/``: ``x / x`` is ``1`` (or a division-by-zero trap if ``x == 0``).

A few identical-operand forms are *intentional* and must not be flagged: ``x != x``
is the canonical NaN test for IEEE-754 floating point, and ``x & x`` may appear in
generated code. Good checkers special-case the floating-point NaN idiom.

# Catching the issue

Clang/clang-tidy has a dedicated check, ``misc-redundant-expression``, and the
compiler warns via ``-Wtautological-compare`` for the identical-operand
comparison cases. cppcheck (``duplicateExpression``), PVS-Studio (V501 "identical
sub-expressions to the left and right of an operator"), and Coverity all detect
it directly and are among the highest-signal warnings those tools emit, since the
pattern has very few legitimate uses. Keep these checks on in CI. In review, be
alert to long boolean chains and to arithmetic over several similarly-named
variables (``x1``/``x2``, ``a.lo``/``a.hi``), which are where the copy-paste slip
hides.

# How to reproduce

Observe that the bounds check repeats ``p->x`` on both sides, so ``p->y`` is
never validated; run ``clang-tidy --checks=misc-redundant-expression`` or
cppcheck.

```c
struct pt { int x, y; };

/* meant to test that BOTH coordinates are inside [0, max) */
int in_bounds(const struct pt *p, int max) {
    return p->x >= 0 && p->x < max &&
           p->x >= 0 && p->x < max;   /* bug: second pair should test p->y */
}
```

