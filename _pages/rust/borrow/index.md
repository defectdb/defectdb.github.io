---
title: "Borrowing"
author: Maxim Menshikov
layout: defect
permalink: /rust/borrow
group:
   - rust
---

Violations of Rust's ownership and aliasing rules — the code the borrow checker rejects at compile time. These defects share one root: an attempt to alias or use a value in a way the type system forbids, whether by holding two mutable references at once, mixing a mutable borrow with a live shared borrow, or reading a value after it has been moved.

Such code never compiles, so the defect surfaces as a build failure rather than a runtime fault, but each case marks a genuine design error about who owns a value and for how long. The fixes — narrowing borrow scopes, cloning, or restructuring ownership — are the everyday vocabulary of working with the checker.
