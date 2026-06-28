---
title: "Slices"
author: Maxim Menshikov
layout: defect
permalink: /array/slice
group:
   - array
---

Defects in slices — sub-ranges that view or borrow part of an array rather than copying it. Trouble comes from bounds that do not match the backing storage and from mutating a slice while assuming it is an independent copy, so a write through one alias unexpectedly changes the original. The shared-buffer aliasing that makes slices cheap is exactly what makes their misuse easy to overlook.
