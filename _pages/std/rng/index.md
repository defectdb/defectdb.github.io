---
title: "Rng"
author: Maxim Menshikov
layout: defect
permalink: /std/rng
group:
   - std
---

Defects in seeding the standard pseudo-random generator. `srand` establishes
the starting point of the sequence and is meant to be called once per program;
reseeding it repeatedly — especially just before each `rand`, often with a
coarse clock value — collapses the apparent randomness, returning identical or
closely correlated values and defeating the purpose of using the generator at
all.

