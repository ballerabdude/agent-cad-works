"""Bought parts: dimensions with their sources, simple envelopes for interference checks, and detailed
models for presentation.

Rule: every number here cites where it came from (datasheet, manual section, vendor STEP, or a drawing the user
supplied). A datasheet drawing is checked against the vendor STEP when one exists (``agentcad.vendor``): in the
project this library came from, a drawing labelled for one actuator turned out to be another model's.

Modules: ``fasteners`` (metric screws), ``extrusions`` (4080 profiles), ``linear`` (MGN12 rail and block),
``belts`` (GT2 pulleys and belts), ``actuators`` (RobStride RS03, NEMA 17).
"""
