---
title: "Observed behaviour doesn't fall within accepted range"
author: Maxim Menshikov
layout: defect
permalink: /logic/complete_behaviour/violation
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: logic.complete_behaviour
group:
   - logic
   - complete_behaviour
---
Real behaviour doesn't match expectation

# Impact

A *complete behaviours* clause asserts that the named behaviours of a function
cover every admissible input: the disjunction of their ``assumes`` guards is a
tautology over the precondition. A violation means the analyzer found an input
that satisfies the precondition yet matches *none* of the declared behaviours —
there is a hole in the specification. Concretely, the function will be exercised
in a situation the author enumerated no contract for, so its behaviour there is
unspecified and unverified. This is a specification-completeness defect: the
guarantees you proved hold only on the cases you listed, and the missing case is
exactly where surprises (wrong results, unhandled states, latent crashes) tend to
hide.

# Vulnerability potential

On its own an incompleteness finding is a verification-coverage gap, not an
exploitable flaw. The security relevance is indirect: the uncovered case is an
input class that was specified and tested less, or not at all, so if a
memory-safety or validation bug exists it is most likely to live there. An
attacker who can steer input into the unhandled region reaches the least-vetted
part of the function. Severity is therefore low by itself but should be resolved,
because completing the behaviours is what forces the missing case to be analyzed.

# Technical details

In ACSL (the specification language Frama-C consumes) a function contract may be
split into named ``behavior`` blocks, each with an ``assumes`` guard selecting
the inputs it describes and ``ensures``/``assigns`` clauses for that case. Two
meta-clauses constrain the set:

- ``complete behaviors b1, b2, ...;`` — at least one guard holds for every input
  allowed by the precondition (the guards *cover* the input space).
- ``disjoint behaviors b1, b2, ...;`` — at most one guard holds for any input
  (the cases do not overlap).

This finding is a failure of the *complete* obligation. The verifier reduces it
to proving ``requires ==> (assumes_1 || assumes_2 || ...)`` and finds a model
where the precondition holds but no ``assumes`` does. The usual cause is an
overlooked boundary or equality case (e.g. covering ``x < 0`` and ``x > 0`` but
forgetting ``x == 0``), or guards written with the wrong relational operators.
The fix is to add or widen a behaviour so the guards exhaust the precondition.

# Catching the issue

Run Frama-C/WP (or another ACSL-aware verifier) with the ``complete behaviors``
clause present; the tool emits a dedicated completeness goal and reports it
unproven when a gap exists, often with a counterexample input. Treat that goal
like any other and fail CI if it does not discharge. When enumerating cases by
hand, cover the relational trichotomy explicitly (``<``, ``==``, ``>``) and the
domain endpoints, since the omitted boundary is the most common hole. Pairing
``complete`` with ``disjoint`` is good practice: together they prove the
behaviours form an exact partition of the input space, so neither gaps nor
overlaps slip through.

# How to reproduce

Observe that the two behaviours cover ``x < 0`` and ``x > 0`` but not ``x == 0``;
``frama-c -wp`` reports the ``complete behaviors`` goal as unproven.

```c
/*@ behavior negative:
  @   assumes x < 0;
  @   ensures \result == -1;
  @ behavior positive:
  @   assumes x > 0;
  @   ensures \result == 1;
  @ complete behaviors negative, positive;   // gap: x == 0 is uncovered
  @ disjoint behaviors negative, positive;
  @*/
int sign(int x) {
    if (x < 0) return -1;
    if (x > 0) return 1;
    return 0;                 /* the unspecified case */
}
```

