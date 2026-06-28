---
title: "States"
author: Maxim Menshikov
layout: defect
permalink: /file/state
group:
   - file
---

Defects that violate a file handle's lifecycle: operating on a descriptor that
is not in the state the operation requires. Closing a file that is already
closed, or reading and writing one that was never successfully opened, leaves
the program acting on an invalid or recycled handle — a path to failed I/O,
double-free-style corruption of kernel resources, and undefined behaviour.

