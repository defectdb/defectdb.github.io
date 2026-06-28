---
title: "Map"
author: Maxim Menshikov
layout: defect
permalink: /std/map
group:
   - std
---

Defects in the use of associative containers, in particular operating on a map
handle that is null. Inserting into or looking up a key in a map that was never
allocated — or whose initialization was skipped on some path — dereferences a
null pointer and crashes, a failure that surfaces only on the branch where the
container was assumed to exist.

