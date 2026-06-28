---
title: "Condition is always false"
author: Maxim Menshikov
layout: defect
permalink: /logic/condition/always_false
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: logic.condition
group:
   - logic
   - condition
---
The corresponding condition is always false

# Impact

A condition provably always false makes the guarded branch *dead code*: the body
of the ``if``, the loop that never iterates, the case that never matches. Whatever
the programmer put there never runs. If that body was important — a special-case
handler, a retry, a cleanup, an input rejection — the program behaves as though
the feature does not exist, while the source still implies it does. As with an
always-true condition, the constant result is usually a symptom of a mis-written
test: the operands cannot satisfy it. The bug stays invisible until someone
relies on the dead branch having executed.

# Vulnerability potential

The security impact depends entirely on what the dead branch was supposed to do.

1. If an always-false condition gates a *security or validation* action —
   ``if (tainted) sanitize(x);`` where ``tainted`` can never be true — the
   sanitization never happens and unsafe data passes through.
2. If it gates *error handling or a bounds check*, the program skips the
   protection and proceeds into code that assumed the check ran, opening the door
   to overflows or invalid-state bugs.

When the branch was genuinely meant to be unreachable (defensive
``if (impossible) abort();``), the always-false result is harmless and even
expected.

# Technical details

The analyzer proves falsity the same way it proves a tautology — by reasoning
about the values the operands can take. Common origins:

- **Contradictory range test.** ``x < 0 && x > 10`` or comparing an enum against
  a value it can never hold.
- **Unsigned underflow assumption.** Expecting a subtraction of ``size_t`` values
  to go negative; it wraps to a huge positive instead, so ``< 0`` is never true.
- **Wrong logical operator.** ``&&`` where ``||`` was intended can make the whole
  expression unsatisfiable.
- **Stale or compile-time constant.** A configuration macro or a variable known to
  the optimizer to be constant in this build fixes the condition to false.

The compiler folds the constant and removes the branch; it may warn via
``-Wtautological-compare``. Note the asymmetry with always-true: here the visible
effect is *missing* behaviour rather than an *extra* always-taken path, which can
make it harder to notice in casual testing.

# Catching the issue

The same toolchain warnings apply: ``-Wtautological-compare``, ``-Wtype-limits``,
and the unsigned-comparison diagnostics catch the arithmetic causes. Static
analyzers report provably-false conditions (PVS-Studio V547 "expression is
always false", Coverity, Clang Static Analyzer, cppcheck), and dead-code /
unreachable-branch detectors flag the body that can never run. Code-coverage
reports are especially useful here, because an always-false branch shows up as a
line that no test ever reaches; investigate every such line rather than excusing
it.

# How to reproduce

Observe that the unsigned subtraction never yields a negative value, so the
underflow-rejecting branch is dead and ``need`` is used unchecked.

```c
#include <stddef.h>

/* want to reject the case where avail < used */
int remaining(size_t avail, size_t used) {
    size_t need = avail - used;   /* wraps to huge value if used > avail */
    if (need < 0) {               /* size_t is unsigned: always false */
        return -1;                /* dead: underflow is never detected here */
    }
    return (int)need;
}
```

