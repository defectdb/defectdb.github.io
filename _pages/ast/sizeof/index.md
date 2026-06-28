---
title: "SizeOf operations"
author: Maxim Menshikov
layout: defect
permalink: /ast/sizeof
group:
   - ast
---

Defects arising from `sizeof` and its operand, where the size actually computed is not the size the author meant. Taking `sizeof` of a pointer instead of the pointed-to buffer, of an array that has decayed to a pointer, or of the wrong type silently produces a plausible but incorrect byte count — feeding undersized allocations, truncated copies, and broken arithmetic that the type system never catches.

