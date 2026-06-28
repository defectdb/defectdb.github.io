---
title: "Observed behaviour matches more than one of disjoint behaviours"
author: Maxim Menshikov
layout: defect
permalink: /logic/disjoint_behaviour/violation
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: logic.disjoint_behaviour
group:
   - logic
   - disjoint_behaviour
---
Observed behaviour is at the intersection of two or more behaviour preconditions

# Impact

A *disjoint behaviours* clause asserts that the named behaviours are mutually
exclusive: no admissible input can match more than one ``assumes`` guard. A
violation means the analyzer found an input that satisfies two (or more) guards
at once. The behaviours then disagree about what the function should do for that
input — each promises its own ``ensures`` — so the specification is internally
contradictory at the overlap. If the two postconditions are compatible the
spec is merely redundant, but if they differ, one of them must be false for that
input, which makes the contract unsatisfiable and any proof built on it suspect.
It also signals that the author's mental case split was wrong.

# Vulnerability potential

This is a specification-consistency defect with no direct security impact. The
risk is that a contradictory contract can let a verifier "prove" properties
vacuously or that an implementation guided by an ambiguous spec handles the
overlapping case inconsistently across versions, eroding trust in the
verification result. There is no attacker-controlled memory or control-flow
consequence inherent to the overlap itself; resolve it to keep the proof sound,
not to close an exploit.

# Technical details

In ACSL a function contract can be partitioned into named ``behavior`` blocks,
each guarded by an ``assumes`` predicate. The ``disjoint behaviors`` meta-clause
demands that the guards never overlap; its dual, ``complete behaviors``, demands
they leave no gap. Together they state that the guards form an exact partition of
the input space.

The verifier reduces disjointness to proving, for every pair, that
``!(assumes_i && assumes_j)`` under the precondition, and reports a violation when
it finds a model satisfying both. The classic cause is using non-strict
relational operators on both sides of a boundary — covering ``x <= 0`` *and*
``x >= 0`` makes ``x == 0`` belong to both — or guards on independent conditions
that the author wrongly assumed were exclusive. The fix is to tighten one guard
(make a bound strict, or add a conjunct) so the cases separate cleanly. Note that
disjointness and completeness pull in opposite directions at boundaries: fixing
an overlap by making a bound strict can open a completeness gap and vice versa,
so both clauses should be checked together.

# Catching the issue

Run Frama-C/WP with the ``disjoint behaviors`` clause; it produces a dedicated
disjointness goal per pair of behaviours and reports the unproven one with a
witness input. Make that goal a CI gate. When writing the guards, use a
consistent convention at every boundary — one side strict, the other non-strict
(``x < 0`` vs ``x >= 0``) — so adjacent cases meet exactly once. Always declare
``complete`` and ``disjoint`` together and verify both, since checking only one
lets the other kind of defect through.

# How to reproduce

Observe that ``x == 0`` satisfies both guards (``x <= 0`` and ``x >= 0``);
``frama-c -wp`` reports the ``disjoint behaviors`` goal as unproven, and the two
behaviours give contradictory results there.

```c
/*@ behavior nonpos:
  @   assumes x <= 0;          // overlaps nonneg at x == 0
  @   ensures \result == 0;
  @ behavior nonneg:
  @   assumes x >= 0;          // overlaps nonpos at x == 0
  @   ensures \result == x;
  @ disjoint behaviors nonpos, nonneg;   // fails: x == 0 matches both
  @*/
int clamp_low(int x) {
    return x < 0 ? 0 : x;
}
```

