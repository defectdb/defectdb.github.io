---
title: "Panics"
author: Maxim Menshikov
layout: defect
permalink: /rust/panic
group:
   - rust
---

Explicit panics — the macros that abort the current task by design rather than through an unexpected fault. They share a mechanism (unwinding or aborting the thread) but differ in intent: `panic!` signals an unrecoverable condition the author chose not to return as an error, while `todo!`, `unimplemented!`, and `unreachable!` are placeholders and assertions that a path is unfinished or should never run.

Each is legitimate in the right place, yet each becomes a defect when it reaches production on a path that real input can drive. A `todo!` left in a shipped function, or an `unreachable!` that turns out to be reachable, is a latent crash that the type system will not catch for you.
