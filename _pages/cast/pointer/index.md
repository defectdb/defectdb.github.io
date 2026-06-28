---
title: "Pointer"
author: Maxim Menshikov
layout: defect
permalink: /cast/pointer
group:
   - cast
---

Conversions between pointers and integers, where an address is reinterpreted as a number. The risk is an implicit pointer-to-integer conversion into a type that may be too narrow to hold a full address, so the value is truncated and can no longer be turned back into a valid pointer — a portability and memory-safety hazard that depends on the platform's pointer width.
