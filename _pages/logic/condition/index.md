---
title: "Conditions"
author: Maxim Menshikov
layout: defect
permalink: /logic/condition
group:
   - logic
---

Defects in the boolean conditions that steer control flow. A condition that is provably always true or always false guards a branch that can never behave as intended — dead code on one side, an unreachable guard on the other — while an assignment slipped into a condition usually betrays a confusion between `=` and `==` that quietly changes both a value and the test.

