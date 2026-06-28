---
title: "C++"
author: Maxim Menshikov
layout: defect
permalink: /cpp
---

Defects that arise from the way C++ binds resources, lifetimes, and types together — a language where the same expressiveness that lets you write zero-overhead abstractions also lets a single missed rule corrupt memory, leak a resource, or invoke undefined behavior with no diagnostic. The entries here span the surface that distinguishes C++ from its peers: object construction and destruction, value semantics and the special member functions they imply, manual and RAII-managed memory, the borrowed-view types of modern standard library, and the concurrency primitives the language leaves you to wield by hand.

The common thread is that C++ trusts the programmer to uphold invariants the compiler will not check — that a pointer outlives the view into it, that an allocator is paired with its matching deallocator, that a base class meant for polymorphic deletion declares a virtual destructor, that a lock order is consistent across threads. Violations rarely fail loudly; they surface as crashes far from their cause, silent data races, or exploitable corruption, which is why this family rewards disciplined idioms — RAII, the rule of zero/three/five, `std::lock`, smart pointers — over manual vigilance.
