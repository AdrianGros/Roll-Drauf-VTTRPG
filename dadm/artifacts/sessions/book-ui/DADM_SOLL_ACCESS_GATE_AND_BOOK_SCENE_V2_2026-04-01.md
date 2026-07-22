# DAD-M Soll: Access Gate and Book Scene V2

Date: 2026-04-01
Phase: SOLL
Status: target-defined

## Objective

Define the target behavior for mandatory key-based registration and the first persistent-book authenticated transition.

## Target State

### S-01

Every self-service registration requires a valid registration key.

Allowed outcomes:

- merge public signup into the key flow
- or redirect public signup into the key flow

Not allowed:

- any route that creates a user without key validation

### S-02

Login success should feel like turning to the next page inside the same book.

Required experience:

- authenticate in the open book
- turn the page
- zoom into a visible dashboard page
- keep menu and content on the page plane

### S-03

The dashboard pilot should match the mockup's logic more than the old app dashboard logic.

Required page composition:

- page-native menu ribbon
- campaign region
- character region
- broad widget region

### S-04

This is a pilot, not the full final world.

The pilot is successful if:

- the user no longer feels dropped into a normal interface immediately after login
- the access gate is no longer bypassable
