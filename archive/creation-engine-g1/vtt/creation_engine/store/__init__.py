"""Persistence adapters of the Creation Engine (PostgreSQL in production).

Only this package and ``transports`` may import Flask/SQLAlchemy code
(registry addendum A1 §7.7, enforced by the import-guard test).
"""
