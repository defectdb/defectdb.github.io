---
title: Null pointer dereference
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr/null_deref
arch:
   - native
vulnerability:
   - High
ddos:
   - High
group_full: mem.ptr
group:
   - mem
   - ptr
---

Dereferencing null pointer might have harmful effect on the application or the
complete operating system.

# Impact
In case there is no page assigned to null address, accessing data by that
address and all adjacent addresses will terminate the application. For the
kernel mode, the defect will panic the kernel.

# Vulnerability potential

This issue has a potential to be a vulnerability.

1. Since the default behavior is to terminate the application or panic the
   kernel, this defect might be used as a part of Denial of Service attack.
2. The termination of application might open other security issues in complex
   systems, leading to the attacker gaining access to the system.
3. If attacker has an access to signal handler, this defect may be used to
   perform remote code execution.

# Technical details

The issue comes from memory management unit (MMU) de-facto conventions. When
such a memory access occurs, the operating system looks up the page in the page
table. The address range of the page containing null address is
historically not mapped to any page on most systems, leading to SIGSEGV signal
(on POSIX systems), which by default terminates an application.
On Windows and Visual C++ compiler with Structured Exception Handling (SEH),
the

## Microcontrollers

Beware that most microcontrollers have null address page mapped to the vector
of interrupt handlers. Changing the value on that address may have serious
impact and may come unattended.



# Catching the issue

There are methods to catch the issue in runtime, however, you must be
assured that the signal handler may actually recover the program from the issue,
otherwise, you risk to have the handler invoked repeatedly.

## Linux

Set up the ``SIGSEGV`` signal handler to catch the issue.

## Windows

Use ``__try``/``__except`` if the compiler supports Structured Exception
Handling (Microsoft Visual C++ does).

# How to reproduce

## C
