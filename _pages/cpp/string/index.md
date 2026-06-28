---
title: "Strings"
author: Maxim Menshikov
layout: defect
permalink: /cpp/string
group:
   - cpp
---

Defects at the seam between C++ types and the C string conventions still pervasive beneath them. These entries concern raw character buffers and the C library functions that operate on them: a buffer that is not guaranteed to carry the terminating null these functions rely on, and formatted output like `sprintf` with `%s` whose length is bounded only by the input, not the destination.

The shared root cause is treating a fixed-size buffer as if its capacity were irrelevant. A read that runs off the end of an unterminated buffer, or a write that exceeds the space reserved for it, yields out-of-bounds access — historically one of the most exploitable classes of bug — which the bounded interfaces (`snprintf`, `std::string`, `std::string_view`) are designed to prevent.
