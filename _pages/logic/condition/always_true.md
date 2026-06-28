---
title: "Condition is always true"
author: Maxim Menshikov
layout: defect
permalink: /logic/condition/always_true
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
The corresponding condition is always true

# Impact

A condition that the compiler or analyzer can prove is always true means the
branch was not really a decision. Two things follow. First, the ``else`` path (or
the code after an early ``return``/``break`` guarded by the condition) is
*dead*: it can never execute, so any logic placed there — error handling, a
fallback, a security check — is silently inert. Second, the always-true result is
usually a symptom: the programmer intended a real test but wrote one that the
operands can never falsify (a wrong comparison, a tautology, a sign or type
mistake, a confusion between a value and its address). The visible behaviour is
"it always takes this branch", which may look fine until the day the input that
was *supposed* to take the other branch arrives.

# Vulnerability potential

Usually this is a logic bug with limited direct security impact, but there are
real exceptions.

1. If the always-true condition is a *security check* — ``if (authorized)`` where
   ``authorized`` can never be false because of a coding mistake — the check
   passes unconditionally and access control is effectively removed.
2. If the dead ``else`` branch contained validation, bounds checking, or error
   handling, that protection is gone and malformed input flows into code that
   assumed it had been rejected.

When the condition is merely redundant (genuinely always true and the other
branch was never meant to run), there is no security relevance.

# Technical details

An analyzer proves a condition constant by tracking value ranges and
relationships along each path. Frequent root causes in C/C++:

- **Type/range tautology.** Comparing an ``unsigned`` value with ``>= 0``, or a
  small enum against a value outside its range, yields a constant the type
  guarantees.
- **Wrong operator.** ``a || b`` where ``a && b`` was meant, or ``!=`` instead of
  ``==``, can collapse to a tautology.
- **Sign/promotion surprises.** Integer promotion and the usual arithmetic
  conversions can make a comparison that looks meaningful constant under the
  actual operand types.
- **Macro expansion.** A macro that expands to a constant, or a configuration
  flag fixed at compile time, makes the condition trivially true in this build.

The compiler legitimately exploits this: it folds the constant, deletes the dead
branch, and may emit ``-Wtautological-compare``. The information is there; the
defect is that the human did not intend it.

# Catching the issue

Enable and act on the compiler warnings: GCC/Clang ``-Wtautological-compare``,
``-Wtype-limits`` (part of ``-Wextra``), and ``-Wtautological-constant-out-of-range-compare``
catch the common range tautologies. Static analyzers (Clang Static Analyzer,
Coverity, PVS-Studio's V547 "expression is always true", cppcheck) report
provably-constant conditions and the dead code they create; coverage tools that
flag unreachable branches give a second, dynamic signal. In review, be
suspicious of any comparison of an unsigned quantity against zero and of branches
whose ``else`` is never observed to run in tests.

# How to reproduce

Observe that ``len >= 0`` is always true for an ``unsigned`` value, so the
error branch is dead and an oversized length is accepted; compile with
``-Wtype-limits``.

```c
#include <stddef.h>
#include <string.h>

void copy(char *dst, const char *src, size_t len) {
    if (len >= 0) {            /* size_t is unsigned: always true */
        memcpy(dst, src, len); /* the "reject huge len" else-branch is dead */
    } else {
        /* unreachable: intended to reject invalid lengths */
        return;
    }
}
```

