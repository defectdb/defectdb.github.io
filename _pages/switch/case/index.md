---
title: "Cases"
author: Maxim Menshikov
layout: defect
permalink: /switch/case
group:
   - switch
---

Defects concerning the individual arms of a `switch`, both their number and
their weight. Too many cases indicate dispatch logic that has outgrown the
construct and become hard to follow, while a case whose body is large or
expensive can prevent the compiler from lowering the switch to an efficient
jump table — trading a constant-time branch for a sequence of comparisons.

