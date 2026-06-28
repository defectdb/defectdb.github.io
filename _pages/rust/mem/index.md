---
title: "Memory"
author: Maxim Menshikov
layout: defect
permalink: /rust/mem
group:
   - rust
---

Low-level `std::mem` operations that step around Rust's ownership and type guarantees. These functions are safe to call in the borrow checker's eyes but carry consequences it cannot police: `mem::forget` suppresses a value's destructor, leaking resources and breaking the RAII contract that frees memory, closes handles, and releases locks; `mem::transmute` reinterprets one type's bytes as another, the bluntest escape hatch in the language and a ready source of undefined behaviour when the layouts or invariants do not line up.
