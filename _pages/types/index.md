---
title: "Types"
author: Maxim Menshikov
layout: defect
permalink: /types
---

Defects where a value is used as a type it does not actually have, or moved between types in ways the language permits but the program's logic does not intend. The type system exists to keep representations and operations consistent; these bugs live where that consistency breaks down — at conversions, assignments, and the boundaries between nominally compatible types.

The common thread is a mismatch that the compiler either cannot see or is willing to accept under an implicit or explicit conversion. The cost ranges from outright rejection to silent truncation, reinterpretation, or loss of precision, with the damage often appearing far from the line where the wrong type first slipped in.

