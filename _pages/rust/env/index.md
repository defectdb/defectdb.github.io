---
title: "Environment"
author: Maxim Menshikov
layout: defect
permalink: /rust/env
group:
   - rust
---

Misuse of the process environment through `std::env`. The case covered here is an empty environment-variable key, which the platform APIs reject: setting a variable whose name is the empty string (or contains an `=` or NUL) panics, turning a configuration slip into a hard runtime failure.
