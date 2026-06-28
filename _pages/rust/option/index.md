---
title: "Option"
author: Maxim Menshikov
layout: defect
permalink: /rust/option
group:
   - rust
---

Defects in handling `Option<T>`, where the absence of a value is forced open instead of being accounted for. Calling `unwrap` (or `expect`) on a `None` panics, converting a representable "no value" case into a crash — the classic substitute for the null-dereference that Rust's type system was designed to make unrepresentable.
