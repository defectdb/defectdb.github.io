---
title: "No proof available"
author: Maxim Menshikov
layout: defect
permalink: /logic/contract/no_proof
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: logic.contract
group:
   - logic
   - contract
---
The contract is violated

# Impact

This finding does not say the contract is broken; it says the verifier *could
not establish that it holds*. A proof obligation was left undischarged. The
practical impact is a loss of assurance: the code may well be correct, but the
guarantee you were buying from formal verification — "this property holds for all
executions" — is absent for this obligation. In a certification or
safety-critical context that gap is itself the defect, because partial proofs
cannot be relied upon. The danger is treating an unproven obligation as if it
were proven and shipping code whose correctness rests on an unverified
assumption that later turns out to be false.

# Vulnerability potential

By itself a missing proof has no direct security impact — it is an absence of
evidence, not a confirmed flaw. The indirect risk is that an undischarged
obligation may be hiding a genuine precondition or bounds violation that a
completed proof would have exposed. If teams routinely accept "unknown" results,
real memory-safety or denial-of-service bugs can pass review under a false sense
of verified safety. The severity therefore tracks whatever the unproven
obligation was guarding, which is why an audit must resolve it rather than
dismiss it.

# Technical details

Deductive verifiers (Frama-C/WP, Why3, Dafny, SPARK) translate each contract
into verification conditions and hand them to automated theorem provers, usually
SMT solvers (Alt-Ergo, Z3, CVC5). A solver returns *valid* (proved), *invalid*
(counterexample, i.e. a real violation), or — crucially — *unknown* / *timeout*.
An "unknown" is not a violation; it is the prover giving up.

## Why proofs fail to close
- **Insufficient annotations.** Loops without a strong enough invariant, or
  callees whose contracts are too weak, leave the prover unable to bridge the
  gap. This is the most common cause and is fixable by strengthening the spec.
- **Incompleteness and resource limits.** First-order arithmetic with
  multiplication, quantifiers, or nonlinear terms is undecidable in general; the
  solver hits its time or memory budget before deciding.
- **Missing lemmas.** Some facts (e.g. properties of modular arithmetic or
  bit operations) must be supplied as lemmas the automated prover cannot
  discover on its own.

The fix is to add the missing invariants, split the goal, supply lemmas, or
discharge the remaining obligation interactively (e.g. in Coq/Isabelle) — not to
silence the warning.

# Catching the issue

Configure the verification pipeline to fail the build on any obligation that is
not *valid*, so "unknown" and "timeout" cannot pass silently — this is the single
most important control. Track the proof-coverage ratio in CI and forbid
regressions. When an obligation will not close automatically, strengthen loop
invariants and callee contracts, raise solver timeouts deliberately, try
alternate back-end provers, or fall back to an interactive proof assistant. As a
defence in depth, keep a runtime check (an ``assert`` of the same property)
compiled into test builds so the unverified obligation is at least exercised
dynamically by fuzzing. Record any obligation that is justified-but-unproven as
an explicit, reviewed deviation rather than an unnoticed gap.

# How to reproduce

Observe that ``frama-c -wp`` cannot prove the ``ensures`` clause because the
loop carries no invariant relating ``found`` to the searched prefix; the result
is "Unknown", not a counterexample, even though the code is in fact correct.

```c
/*@ requires n >= 0;
  @ requires \valid_read(a + (0 .. n-1));
  @ ensures  \result == 1 <==> (\exists integer k; 0 <= k < n && a[k] == x);
  @*/
int contains(const int *a, int n, int x) {
    int found = 0;
    /* no loop invariant supplied -> WP cannot discharge the postcondition */
    for (int i = 0; i < n; i++)
        if (a[i] == x)
            found = 1;
    return found;
}
```

