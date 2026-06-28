---
title: "Destructors"
author: Maxim Menshikov
layout: defect
permalink: /cpp/dtor
group:
   - cpp
---

Defects where a destructor does something it must never do — chiefly, let an exception escape. Since C++11 destructors are implicitly `noexcept`, so an exception that propagates out of one calls `std::terminate`, and during stack unwinding a second in-flight exception is fatal outright, making "throwing destructor" a reliable path to an abrupt process death.
