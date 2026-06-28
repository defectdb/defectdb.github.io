---
title: "Result"
author: Maxim Menshikov
layout: defect
permalink: /rust/result
group:
   - rust
---

Defects in handling `Result<T, E>`, where a fallible operation's outcome is unwrapped without its other arm being considered. Calling `unwrap` on an `Err` panics, discarding a recoverable error and crashing instead of propagating it; unwrapping when the value is `Ok` is the inverse mistake — asserting failure on a success, or unwrapping defensively where the error case can never be meaningfully reached. Both signal that the error contract was asserted away rather than handled.
