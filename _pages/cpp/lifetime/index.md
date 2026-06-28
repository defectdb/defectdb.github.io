---
title: "Lifetime"
author: Maxim Menshikov
layout: defect
permalink: /cpp/lifetime
group:
   - cpp
---

Defects where a non-owning view outlives the object it refers to. Borrowed-reference types like `std::string_view` and `std::span` hold a pointer and a length but take no ownership, so binding one to a temporary — or to a local that goes out of scope first — leaves it pointing at storage that has already been destroyed, a dangling read that typically survives testing and fails in production.
