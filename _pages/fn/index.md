---
title: "Functions"
author: Maxim Menshikov
layout: defect
permalink: /fn
---

Defects rooted in the contract of a function call: what is passed in, what
comes back, and how long the call is allowed to take. A function boundary is a
promise between caller and callee, and these entries collect the ways that
promise is quietly broken without the compiler objecting.

They span the three sides of that contract. Arguments go wrong when values are
supplied that the callee cannot accept or when an overload is resolved against
the programmer's intent, so the wrong code runs on the wrong data; results go
wrong when a return value that reports success, failure, or a needed output is
discarded; and timing goes wrong when a call that can block indefinitely is
made with no timeout, leaving the program to hang on a dependency that never
answers.

