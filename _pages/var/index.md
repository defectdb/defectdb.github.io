---
title: "Variables"
author: Maxim Menshikov
layout: defect
permalink: /var
---

Defects in how variables are declared, initialized, used, and torn down — the everyday handling of named storage that underpins almost all other code. These bugs are rarely about a single dramatic operation; they accumulate in the small decisions about when a variable holds a meaningful value, where it can be seen, how large it is, and when its resources are released.

The entries here span the full lifecycle of a variable: confusing empty or null values for valid ones, reading state that was never initialized, leaking visibility beyond the scope that should contain it, shadowing one name with another, over-sizing storage, mishandling static and interface-typed values, and deferring cleanup until it no longer runs when intended. What unites them is that the variable compiles and looks ordinary, while its value, lifetime, or reach quietly violates what the surrounding code assumes.

