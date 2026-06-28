---
title: "Assignment in condition"
author: Maxim Menshikov
layout: defect
permalink: /logic/condition/assignment
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: logic.condition
group:
   - logic
   - condition
---
Assignment in condition is suspicious

# Impact

An assignment used where a comparison was meant — the classic ``if (x = y)``
instead of ``if (x == y)`` — does two harmful things at once. It overwrites
``x`` as a side effect, mutating state the author did not intend to touch, and it
makes the condition evaluate the *assigned value* rather than a comparison, so
the branch is taken based on "is ``y`` non-zero" instead of "does ``x`` equal
``y``". The result is a test that almost always goes the wrong way: a non-zero
right-hand side makes the condition perpetually true, a zero one perpetually
false, and the variable silently loses its previous contents. Because the code
*looks* like a comparison, the bug survives casual reading.

# Vulnerability potential

This pattern has real security history; it is how the 2003 attempt to backdoor
the Linux kernel was disguised (``if ((options == (__WCLONE|__WALL)) && (current->uid = 0))``,
a ``=`` masquerading as ``==`` that silently granted root).

1. When the condition is a security or authorization check, the assignment can
   both clobber the credential being tested and force the branch outcome,
   bypassing the check or escalating privilege.
2. The unintended write corrupts program state — a length, a flag, a pointer —
   which downstream code then trusts, leading to logic errors or memory bugs.
3. As a deniable construct, it is attractive to an attacker submitting a
   malicious patch, because it reads as a harmless comparison.

# Technical details

In C and C++ assignment is an *expression* whose value is the value assigned, and
any scalar value is implicitly convertible to ``bool`` in a condition. So
``if (x = y)`` is well-formed: it assigns ``y`` to ``x`` and then tests the
result for non-zero. The grammar makes ``=`` (assignment) and ``==`` (equality)
a single keystroke apart, which is why the typo is so common. Languages that
forbid this — by requiring a boolean condition and making assignment a statement,
not an expression (Python, Go, Rust, Java for non-boolean operands) — eliminate
the defect at the source.

## Intentional assignments
Not every assignment in a condition is a bug: ``while ((c = getchar()) != EOF)``
and ``if ((p = malloc(n)) == NULL)`` are idiomatic. The signal that
distinguishes intent is whether the assignment's result is *further compared*.
Tools and conventions therefore key off a "bare" assignment used directly as the
truth value, and the common defensive idiom is to wrap deliberate assignments in
an extra pair of parentheses to say "I meant this".

# Catching the issue

Compile with ``-Wparentheses`` (in GCC/Clang ``-Wall``), which warns
"suggest parentheses around assignment used as truth value" and is silenced by
the extra-parentheses idiom for deliberate cases. Clang's
``-Wsmetimes-uninitialized`` and clang-tidy's
``bugprone-assignment-in-if-condition`` are more targeted. Static analyzers
(cppcheck, PVS-Studio V559, Coverity) flag it directly. A robust review
convention is *Yoda conditions* — writing ``if (CONST == x)`` so that a slipped
``=`` becomes a compile error (``CONST = x`` is not assignable). MISRA C
(Rule 13.4) prohibits using the result of an assignment, ruling the construct out
in safety-critical code.

# How to reproduce

Observe that the check meant to compare ``role`` against ``ADMIN`` instead
assigns it, clobbering ``role`` and making the branch unconditionally taken;
build with ``-Wall`` to see the warning.

```c
#include <stdio.h>

#define ADMIN 1

int main(void) {
    int role = 0;                 /* an unprivileged user */
    if (role = ADMIN) {           /* bug: '=' should be '=='            */
        printf("granted admin\n");/* always runs, and role is now ADMIN */
    } else {
        printf("denied\n");
    }
    return 0;
}
```

