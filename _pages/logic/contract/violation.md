---
title: "Contract violation"
author: Maxim Menshikov
layout: defect
permalink: /logic/contract/violation
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: logic.contract
group:
   - logic
   - contract
---
The contract is violated

# Impact

A function contract is the agreement between a function and its callers: a
*precondition* the caller must satisfy before the call, a *postcondition* the
function guarantees on return, and the assigns/frame clause bounding what it may
modify. A contract violation means one side broke the deal. If a precondition is
violated, the function is run on inputs it was never designed to handle, so any
guarantee it makes is void and its behaviour is, from that point, undefined by
its own specification. If a postcondition is violated, the function returned a
result that callers are entitled to trust but must not. Either way, downstream
code proceeds on a false assumption, which surfaces as wrong output, corrupted
state, or a crash whose origin is some distance from the actual violation.

# Vulnerability potential

Contracts frequently encode exactly the assumptions that keep code memory-safe,
so violating them is a recognized route to exploitable bugs.

1. A violated precondition such as "``len <= capacity``" or "``ptr != NULL``"
   means the body skips bounds or null reasoning it was allowed to skip,
   producing buffer overflows or null dereferences on the violating input.
2. A violated postcondition (e.g. a function that promises a NUL-terminated
   string or a value within range but does not deliver it) propagates a
   dangerous value into callers that validated nothing because the contract said
   they need not.
3. When the violation is reachable from untrusted input and the failure mode is
   an abort or an unhandled error, it is a denial-of-service primitive.

# Technical details

Contracts formalize design-by-contract (Meyer) and Hoare-triple reasoning
``{P} S {Q}``: given precondition ``P``, statement ``S`` establishes
postcondition ``Q``. In C this is expressed with specification languages such as
ACSL (consumed by Frama-C) using ``requires``/``ensures``/``assigns`` clauses in
``/*@ ... */`` annotations; C++ has contract assertions
(``pre``/``post``/``contract_assert``); other ecosystems use JML, Spec#, or
runtime contract libraries.

A violation is detected one of two ways. *Deductive verification* tries to prove,
for all inputs, that the code respects the contract; a violation here is a proof
that some execution breaks it. *Runtime checking* instruments the boundaries and
traps a violation when it actually occurs during execution. The first is
exhaustive but needs annotations strong enough to close the proof; the second
only sees violations you manage to trigger.

## Who is at fault
Blame depends on which clause failed. A failed ``requires`` is the *caller's*
bug: it passed illegal arguments. A failed ``ensures`` with a satisfied
``requires`` is the *callee's* bug: it accepted valid input and still failed to
deliver. Correctly attributing the violation is essential to fixing the right
side of the interface.

# Catching the issue

For C, write the contracts in ACSL and run Frama-C/WP to discharge them with SMT
solvers; an unprovable goal pinpoints the violating clause. For runtime defence,
compile contract checks in (C++26 contract assertions, or hand-written
``assert``-style pre/post guards at function boundaries) and keep them enabled in
test and CI builds, then drive them with fuzzing so reachable violations
actually fire. Static analyzers (Clang Static Analyzer, Coverity, PVS-Studio)
infer and check many implicit contracts — null-ness, range, taint — without
annotations. In code review, treat every documented precondition as something a
caller can violate and confirm each call site honors it.

# How to reproduce

Observe that ``main`` violates the ``requires n >= 0`` precondition; Frama-C/WP
reports the ``requires`` goal as unproven at the call site, and at runtime the
function divides by a smaller-than-expected count and reads out of bounds.

```c
/*@ requires n >= 1;
  @ requires \valid_read(a + (0 .. n-1));
  @ ensures  \result == (\sum(0, n-1, \lambda integer k; a[k])) / n;
  @*/
int average(const int *a, int n) {
    int sum = 0;
    for (int i = 0; i < n; i++)
        sum += a[i];
    return sum / n;            /* division by zero if precondition broken */
}

int main(void) {
    int a[3] = {10, 20, 30};
    return average(a, 0);      /* violates "requires n >= 1" -> div by zero */
}
```

