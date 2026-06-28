---
title: "Logic"
author: Maxim Menshikov
layout: defect
permalink: /logic
---

Defects in the reasoning a program encodes — its assignments, conditions, invariants, and the contracts and behavioural specifications it is supposed to satisfy. These are not syntax errors but flaws in meaning: code that compiles and runs yet does not say, or do, what the logic requires.

The unifying theme is a mismatch between intent and effect. A condition that is always true or always false, an assignment whose result is never used or never justified, an invariant that fails to hold, a contract left unproven or outright violated, observed behaviour that escapes the accepted range or matches two cases meant to be disjoint — each marks a place where the program's stated logic and its actual behaviour have diverged.

