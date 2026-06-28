---
title: "Memory"
author: Maxim Menshikov
layout: defect
permalink: /mem
---

Defects in the manual management of dynamic memory — how blocks are allocated, freed, and reached through pointers. When the language leaves ownership and lifetime to the programmer, the gap between when storage is valid and when it is still referenced becomes the source of the most damaging and hardest-to-reproduce bugs in a program.

The entries divide into two themes: the life cycle of an allocation — leaking a block by losing its last reference, or releasing one twice — and the pointers that name it, including dereferencing a possibly-null pointer, holding a dangling pointer to freed memory, or comparing pointers in suspicious ways. Together they cover the corruption, crashes, and exploitable conditions that follow from a mismatch between a block's real lifetime and the program's belief about it.
