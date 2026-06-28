---
title: "Free"
author: Maxim Menshikov
layout: defect
permalink: /mem/block/free
group:
   - mem
   - block
---

Defects in releasing an allocated block back to the allocator. The central case is a double free — handing the same address to `free` twice — which corrupts allocator bookkeeping and is a well-known route to undefined behaviour and exploitable heap state. It usually traces to muddled ownership, where two code paths each believe they are responsible for the same block.
