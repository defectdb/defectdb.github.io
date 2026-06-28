---
title: "Marshalling"
author: Maxim Menshikov
layout: defect
permalink: /csharp/marshal
group:
   - csharp
---

Defects at the managed/native interop boundary, where the `Marshal` API copies data and hand-manages memory that the garbage collector does not track. Here the runtime's safety guarantees end: lifetimes, layouts, and ownership become the programmer's responsibility, and a small mistake reads or frees the wrong bytes.

Allocations obtained through `Marshal` must be released on every path or they leak, and `Marshal.PtrToStructure` trusts the caller's claim that the pointer addresses a fully initialized block of the declared layout — a wrong type, size, or null leads straight to corruption or an access violation.

