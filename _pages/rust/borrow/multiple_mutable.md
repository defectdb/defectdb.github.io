---
title: "Multiple mutable borrows"
author: Maxim Menshikov
layout: defect
permalink: /rust/borrow/multiple_mutable
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: rust.borrow
group:
   - rust
   - borrow
---
Two or more `&mut` references to the same value coexist; Rust's borrow checker forbids this

# Impact

This is a compile-time error, not a runtime defect: a program that violates the
aliasing rule (error `E0499`) will not build, so it can never ship or run in the
first place. The practical impact is therefore limited to developer friction —
the code does not compile until the conflicting borrows are restructured.

Conceptually the rule exists because two live `&mut` references to the same
location would allow unsynchronized aliased mutation. In a language without this
check (or in `unsafe` code that bypasses it) the same pattern enables iterator
invalidation, data races, and torn writes. The borrow checker turns that whole
class of latent bugs into a build failure.

# Vulnerability potential

This defect has essentially no security relevance on its own. The compiler
rejects the code, so no vulnerable binary is produced. The only way the
underlying aliased-mutation hazard reaches a running program is by deliberately
circumventing the checker with `unsafe` (raw pointers, `transmute`, or
`UnsafeCell` misuse), at which point the relevant defect is the unsafe code, not
this compile error.

# Technical details

Rust enforces "Aliasing XOR Mutability": at any point a value may have either
any number of shared `&` references or exactly one exclusive `&mut` reference,
never both and never two exclusive ones. The borrow checker (operating on MIR
with Non-Lexical Lifetimes since Rust 2018) computes the live region of each
borrow and reports `E0499 — cannot borrow `x` as mutable more than once at a
time` when two `&mut` regions overlap.

## Why the guarantee matters

The single-writer invariant is what lets the compiler assume a `&mut T` does not
alias anything else, enabling `noalias`-style optimizations and making data
races impossible in safe code. NLL makes the analysis flow-sensitive, so a
borrow ends at its last use rather than at the end of the lexical scope, which
accepts more correct programs while still rejecting genuine overlap.

# Catching the issue

The Rust compiler (`rustc`) itself is the detector — no extra tooling is
required. The build fails with error `E0499` and a span pointing at both
borrows. `cargo check` surfaces it fastest. To fix, sequence the borrows so one
ends before the next begins, split a struct into disjoint fields (the compiler
understands per-field borrows), or use an interior-mutability type such as
`RefCell`/`Cell` (single-threaded) or `Mutex`/`RwLock` (shared) when genuinely
concurrent mutation is required.

# How to reproduce

Compile the following; observe the compiler reject it with `E0499`.

```rust
fn main() {
    let mut value = 10;
    let a = &mut value;
    let b = &mut value; // error[E0499]: cannot borrow `value` as mutable more than once
    *a += 1;
    *b += 1;
    println!("{a} {b}");
}
```
