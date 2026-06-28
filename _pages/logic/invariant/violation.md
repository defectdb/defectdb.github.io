---
title: "Invariant check failed"
author: Maxim Menshikov
layout: defect
permalink: /logic/invariant/violation
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: logic.invariant
group:
   - logic
   - invariant
---
Invariant check failed

# Impact

An invariant is a property the author assumes always holds at a given program
point (a loop invariant, a class invariant, a data-structure consistency rule).
When the check fails, the program has demonstrably reached a state its author
believed impossible. What happens next depends on enforcement. A debug-time
``assert`` aborts the process via ``SIGABRT``. A release build, where the check
is usually compiled out, keeps running on top of the broken assumption: it
produces wrong results, corrupts the data structure further, or crashes much
later at a point that has no obvious connection to the real fault. The latter is
the dangerous case, because the damage is silent and the bug is hard to trace.

# Vulnerability potential

A broken invariant is a state-integrity failure, and integrity failures are a
common root of security bugs.

1. If the invariant guarded a value later used for memory access — a buffer
   length, an index bound, a type tag, a reference count — continuing past the
   violation can turn it into an out-of-bounds access, type confusion, or
   use-after-free under attacker influence.
2. When invariants are enforced with ``assert``/``abort()``, any input that can
   reach the violation gives an attacker a reliable crash, i.e. a denial of
   service.
3. Invariants compiled out under ``NDEBUG`` silently disappear in production. A
   check that protected security-relevant state in testing provides no
   protection in the shipped binary, so the gap is only exercised by attackers.

# Technical details

The notion of an invariant comes from Hoare logic and design-by-contract: it is
an assertion attached to a program point that the surrounding code is obliged to
maintain. A loop invariant holds before and after every iteration; a class
invariant holds whenever a method is not executing; a representation invariant
captures the consistency rules of a data structure (e.g. "a red node has no red
child" in a red-black tree).

A violation means one of two things: either the code that was supposed to
re-establish the invariant has a bug, or the invariant itself is wrong (too
strong for the real states the program can reach). Both are genuine defects, but
they call for opposite fixes.

## Checked vs. unchecked invariants
In C/C++ the usual tool is the ``assert`` macro, which expands to nothing when
``NDEBUG`` is defined. This makes invariants a debug-only safety net by default.
C++26 contracts and tools such as Frama-C/ACSL let invariants be stated formally
and either checked at runtime or discharged statically, removing the
"disappears in release" problem.

# Catching the issue

Keep invariant checks active in the builds you actually test, including
release-with-assertions CI configurations, instead of relying only on debug
builds. Fuzzing (libFuzzer, AFL++) combined with live assertions is highly
effective at driving programs into states that violate them. For the most
critical structures, state the invariant formally and discharge it with a
deductive verifier (Frama-C/WP, model checkers) so violations are proven
impossible rather than merely untriggered. UBSan and ASan will not flag the
logical violation itself, but they catch the memory errors a missed invariant
frequently produces downstream, which helps localize the root cause.

# How to reproduce

Observe that the loop invariant ``sum == sum of a[0..i)`` is broken by an
off-by-one bug; with assertions enabled the program aborts, and with ``-DNDEBUG``
it silently returns a wrong total.

```c
#include <assert.h>
#include <stdio.h>

int sum_to(const int *a, int n) {
    int sum = 0;
    for (int i = 0; i <= n; i++) {   /* bug: should be i < n */
        /* invariant: sum holds the total of a[0 .. i)            */
        assert(i <= n && "index walked past the array");
        sum += a[i];                 /* reads a[n], one past the end */
    }
    return sum;
}

int main(void) {
    int a[3] = {1, 2, 3};
    printf("%d\n", sum_to(a, 3));    /* expects 6, reads out of bounds */
    return 0;
}
```

