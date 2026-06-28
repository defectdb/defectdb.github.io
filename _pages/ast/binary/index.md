---
title: "Binary operations"
author: Maxim Menshikov
layout: defect
permalink: /ast/binary
group:
   - ast
---

Defects in binary operations — any construct of the form `a op b` — where the operator and its two operands form a combination that cannot be what the author intended. The most telling case is two structurally identical subexpressions on either side of an operator, where comparing, subtracting, or `and`-ing a value against itself yields a constant or a no-op and almost always marks a copy-paste slip or a wrong operand.

