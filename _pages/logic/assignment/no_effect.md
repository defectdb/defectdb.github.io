---
title: "Unreasoned assignment"
author: Maxim Menshikov
layout: defect
permalink: /logic/assignment/no_effect
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: logic.assignment
group:
   - logic
   - assignment
---
This assignment result might be unused or assignment might not take effect

# Impact

This covers assignments that accomplish nothing: a self-assignment
``x = x``, a write to a copy that the caller never sees, an update to a field
that is immediately recomputed, or a store the compiler can prove has no
observable effect. The assignment looks like it changes state but does not.
Functionally the program runs as if the line were absent, which is benign in
isolation but almost always means the author *expected* an effect that is not
happening — the wrong variable was assigned, a pointer/reference was needed
instead of a value, or a missing ``volatile`` made the write disappear. The
consequence is a silent divergence between what the code says it does and what it
actually does.

# Vulnerability potential

Mostly a correctness and clarity issue, but the "intended effect did not happen"
reading carries some risk.

1. If the assignment was meant to *update a security-relevant value* — clearing a
   flag, lowering a privilege level, invalidating a cached credential — and it
   silently has no effect, the system stays in the more-privileged or stale state.
2. A missing ``volatile`` on a memory-mapped register or a flag shared with a
   signal handler/another thread lets the compiler optimize the write away, so a
   needed hardware or synchronization side effect never occurs, which can defeat a
   safety or security action.

When the assignment is genuinely redundant (e.g. defensive self-assignment), it
has no security relevance.

# Technical details

An assignment has no effect when its target's new value equals its old value, or
when the target is not observable after the store. The compiler establishes this
with value and liveness analysis and removes the write under the as-if rule.

## Common shapes
- **Self-assignment.** ``x = x;`` or ``obj.field = obj.field;`` — frequently a
  typo for assigning a *different* member (``a.x = b.x``).
- **Write to a by-value copy.** Modifying a struct received by value, or a
  loop-induction copy, when the caller's object was meant to change; the mutation
  dies with the copy.
- **Optimized-away write.** A store to a variable later overwritten on every
  path, or to plain (non-``volatile``) memory that models hardware/shared state,
  which the optimizer legally drops because it sees no reader.
- **Computed-then-discarded.** ``a + b;`` style statements, or an assignment to a
  temporary that is never used.

The ``volatile`` qualifier exists to forbid this elimination where the write is
the point (MMIO, ``sig_atomic_t`` flags); leaving it off is a frequent root
cause.

# Catching the issue

Compilers warn on the obvious cases: Clang's ``-Wself-assign`` and
``-Wself-assign-field``, and ``-Wunused-value`` for expression statements with no
effect. Static analyzers go further — cppcheck ``selfAssignment`` /
``redundantAssignment``, PVS-Studio V570/V587, Coverity, and the Clang Static
Analyzer flag assignments whose value is unobservable. For the pass-by-value
trap, prefer references/pointers and let ``-Wunused-but-set-parameter`` help. For
the ``volatile`` trap, review every write to hardware registers and to flags
shared with signal handlers or other threads, and confirm the qualifier (or a
proper atomic) is present. In review, treat a no-effect assignment as a question:
what state was supposed to change here?

# How to reproduce

Observe that ``normalize`` mutates a by-value copy, so the caller's struct is
unchanged — the assignment has no effect outside the function. Build with
``-Wall``.

```c
#include <stdio.h>

struct point { int x, y; };

/* takes the struct BY VALUE: assignments touch a local copy only */
void normalize(struct point p) {
    p.x = 0;          /* no effect on the caller's object */
    p.y = 0;
}

int main(void) {
    struct point a = {3, 4};
    normalize(a);                 /* intended to reset a, but does nothing */
    printf("%d %d\n", a.x, a.y);  /* prints "3 4", not "0 0" */
    return 0;
}
```

