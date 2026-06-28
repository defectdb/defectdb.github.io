---
title: "Switch"
author: Maxim Menshikov
layout: defect
permalink: /switch
---

Defects in multi-way branch constructs, where the shape of a `switch` rather
than any single expression is the problem. As the number and weight of branches
grow, the construct stops being a clean dispatch and becomes a maintenance and
performance liability.

The entries here concern the cases themselves: a switch carrying too many
branches signals logic that has outgrown the construct and likely wants a table
or polymorphism instead, while individual cases holding non-trivial bodies can
defeat the compiler's jump-table optimisation and turn dispatch into a chain of
comparisons.

