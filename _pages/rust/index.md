---
title: "Rust"
author: Maxim Menshikov
layout: defect
permalink: /rust
---

Defects in Rust code, where the compiler's ownership and type guarantees rule out whole classes of bugs but leave room for logic errors, deliberate escape hatches, and the deliberate-crash macros that the language hands to the programmer. Rust eliminates data races and use-after-free in safe code, so the remaining defects cluster around what the borrow checker rejects, what `unsafe` lets back in, and what happens when a program reaches a state its author decided not to handle.

The entries here span the ownership model itself — moves and aliasing rules enforced by the borrow checker — and the runtime side of fallibility: `Option` and `Result` unwrapped without their failing case handled, panics raised explicitly or through `todo!`, `unimplemented!`, and `unreachable!`, raw-pointer dereferences that bypass reference guarantees, `mem` operations that subvert ownership, environment misuse, and debugging aids left in shipped code.
