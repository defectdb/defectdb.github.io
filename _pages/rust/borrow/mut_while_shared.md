---
title: "Mutable borrow while shared borrow exists"
author: Maxim Menshikov
layout: defect
permalink: /rust/borrow/mut_while_shared
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
A `&mut` reference is taken while a `&` reference to the same value is still live

# Impact

This is a compile-time error (`E0502`), so the offending program never builds
and never runs. The only direct impact is that the developer must restructure
the code before it compiles.

The rule it enforces prevents a real hazard: mutating a value through `&mut`
while a `&` reader still holds a reference into it. In an unchecked language this
is the classic source of iterator invalidation — e.g. pushing to a vector while
iterating it can reallocate the backing buffer and leave the reader pointing at
freed memory. Rust converts that use-after-free risk into a build failure.

# Vulnerability potential

No security relevance in safe Rust: the code is rejected at compile time, so no
exploitable artifact exists. The underlying read-during-write hazard only
matters if the check is bypassed with `unsafe`, in which case the unsafe block —
not this diagnostic — is the defect to audit.

# Technical details

Under "Aliasing XOR Mutability", a live shared borrow `&T` guarantees the value
is immutable for the borrow's whole region, so the compiler refuses to hand out
a `&mut T` that overlaps it. The check is flow-sensitive thanks to Non-Lexical
Lifetimes: the shared borrow is considered live only up to its last actual use,
so a `&mut` taken strictly after the last read of the `&` is accepted.

## Common trigger

The textbook case is mutating a collection while a reference into it is held —
for example calling `Vec::push` (which may reallocate) while an element
reference obtained earlier is still in scope. The reallocation would dangle the
element reference; the borrow checker forbids the `&mut self` call for exactly
that reason.

# Catching the issue

`rustc`/`cargo check` reports `E0502 — cannot borrow `x` as mutable because it is
also borrowed as immutable`, with spans for both borrows. Fixes: finish using
the shared borrow before taking the mutable one (often just reorder statements),
copy/clone the small value you read so no reference is held, scope the reader in
its own block, or use `RefCell`/`Mutex` when interleaved access is genuinely
needed.

# How to reproduce

Compile the following; the borrow checker rejects it with `E0502`.

```rust
fn main() {
    let mut v = vec![1, 2, 3];
    let first = &v[0];   // shared borrow of v
    v.push(4);           // error[E0502]: needs &mut v while `first` is still live
    println!("{first}"); // use that keeps the shared borrow alive
}
```
