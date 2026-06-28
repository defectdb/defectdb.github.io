---
title: "unreachable! reached"
author: Maxim Menshikov
layout: defect
permalink: /rust/panic/unreachable
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: rust.panic
group:
   - rust
   - panic
---
unreachable! aborts at runtime; the assumed invariant was violated

# Impact

`unreachable!()` expands to a `panic!` with the message
`internal error: entered unreachable code`. It marks a code path the author
believes can never execute (an exhaustive match's impossible arm, a state machine
transition that "can't happen"). When the assumption is wrong and the path *is*
reached, the thread panics — unwinding to thread death, or aborting the whole
process under `panic = "abort"`; a main-thread panic exits with code 101.

Reaching an `unreachable!` always means a real invariant was violated, so it is
both a crash *and* a signal that the program's model of its own state is wrong.
Critically, `unreachable!()` is the *safe* macro — it panics. It must not be
confused with the `unsafe` intrinsic `std::hint::unreachable_unchecked()`, whose
violation is undefined behavior rather than a clean panic.

# Vulnerability potential

1. **Denial of service.** If an input or sequence of operations can drive
   execution into a branch the developer marked unreachable, the resulting panic
   crashes the request or process (under `panic = "abort"` / on a critical
   thread). Reachability of "impossible" states is exactly the kind of edge case
   attackers probe for, making this a plausible DoS.

The safe `unreachable!()` is memory-safe, so its vulnerability rating is Low and
the risk is availability. (By contrast, `hint::unreachable_unchecked()` reached
with a false assumption is UB and would warrant a much higher rating — but that
is a different, `unsafe` defect.)

# Technical details

`unreachable!()` is a thin wrapper over `panic!` evaluating to the never type
`!`, so it fits any expression position — convenient for the final arm of a match
the compiler cannot prove exhaustive, or after a loop that "always" returns. It
crashes through the standard panic machinery and obeys the crate's
`panic = "unwind"`/`"abort"` strategy.

## Safe vs. unchecked

| Form | On reach |
| --- | --- |
| `unreachable!()` (macro, safe) | Panics with a message |
| `std::hint::unreachable_unchecked()` (intrinsic, `unsafe`) | Undefined behavior — the compiler assumes it cannot happen and may miscompile |

Use the macro unless a measured optimization genuinely requires the intrinsic and
the invariant is *provably* upheld; otherwise the unchecked form turns a logic
bug into memory unsoundness.

# Catching the issue

## Lint and review

`clippy::unreachable` (restriction lint) flags the macro so each use is reviewed
for whether the "impossible" arm truly is impossible. Prefer making the
unreachability *structural* — match on a smaller enum, use the type system to
exclude invalid states — so no runtime assertion is needed at all.

## Prefer typed exhaustiveness

Where possible, restructure so the compiler proves exhaustiveness (e.g. matching
all variants of an `enum` without a catch-all), eliminating the need for
`unreachable!`. When a guard is still warranted, `unreachable!("why")` with an
explanatory message aids debugging, and tests should attempt to reach the branch
to confirm it cannot.

# How to reproduce

Run the following; the "impossible" arm is in fact reachable and panics.

```rust
fn classify(n: i32) -> &'static str {
    match n % 2 {
        0 => "even",
        1 => "odd",
        _ => unreachable!(), // wrong: n % 2 can be -1 for negative n
    }
}

fn main() {
    println!("{}", classify(-3)); // panic: internal error: entered unreachable code
}
```
