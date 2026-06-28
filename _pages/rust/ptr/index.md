---
title: "Pointers"
author: Maxim Menshikov
layout: defect
permalink: /rust/ptr
group:
   - rust
---

Raw-pointer defects, where code drops out of the reference model into `unsafe` territory and dereferences a null pointer. Unlike Rust's references, raw pointers carry no validity or non-null guarantee, so reading or writing through one that is null is undefined behaviour — typically a segmentation fault, and the kind of memory error safe Rust exists to prevent.

The cases here distinguish the operations that trigger it: copying a null pointer is harmless until it is used, whereas reading or writing through it dereferences invalid memory, with the write being the more dangerous because it can corrupt state rather than merely crash.
