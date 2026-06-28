---
title: "Arrays"
author: Maxim Menshikov
layout: defect
permalink: /array
---

Defects that arise when indexed, contiguous collections are accessed or reshaped — the bounds, offsets, and sub-ranges through which array elements are reached. Because an array is just a base address and a length, almost every fault here is a question of whether a computed position actually lies inside the data the program owns.

The entries split along that line: addressing an individual element by an index that is negative or past the end, and carving out sub-views whose start, length, or mutation does not match the underlying storage. In unmanaged languages both lead straight to out-of-bounds reads and writes; in managed ones they surface as exceptions or quietly wrong results.
