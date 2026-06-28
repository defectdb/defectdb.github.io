---
title: "Allocation"
author: Maxim Menshikov
layout: defect
permalink: /std/alloc
group:
   - std
---

Defects in calls to the standard allocator where the requested size is
degenerate. Asking `malloc` or its relatives for zero bytes is legal but
implementation-defined: the call may return a null pointer or a unique
non-null pointer that must still be freed, so code that branches on the result
as if it signalled failure — or that dereferences it — is wrong on at least
one conforming platform.

