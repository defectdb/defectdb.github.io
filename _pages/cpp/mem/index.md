---
title: "Memory"
author: Maxim Menshikov
layout: defect
permalink: /cpp/mem
group:
   - cpp
---

Defects in manual memory management, where allocation and release must be paired exactly and the language checks nothing. The representative case is a mismatched allocator and deallocator — freeing with `delete` what was made with `new[]`, or with `free` what came from `new` — which corrupts the heap or skips destructors and is undefined behavior, the kind of mistake RAII and smart pointers exist to make impossible.
