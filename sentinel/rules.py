"""Transparent event-level rules, evaluated using event time."""

import numpy as np
import pandas as pd

RULES = {
    "R1": ("Repeated authentication failures", 65, "Check failed sign-ins and the affected identity."),
    "R2": (
        "High-frequency discovery",
        60,
        "Verify whether the discovery sequence belongs to approved automation.",
    ),
    "R3": (
        "New source IP outside business hours",
        45,
        "Validate the source address and the user's working hours.",
    ),
    "R4": (
        "Sensitive action with unusual context",
        70,
        "Review the change request and resulting resource permissions.",
    ),
    "R5": (
        "Rapid activity across compartments",
        55,
        "Check whether cross-compartment access is expected for this identity.",
    ),
}


def evaluate_rules(df, features, context):
    known = df.principal_name.ne("unknown")
    sensitive = df.event_name.str.contains(r"^(?:CreatePolicy|UpdatePolicy|Delete|UpdateUser)", regex=True)
    masks = {
        "R1": known & context.failures_10m.ge(5),
        "R2": known & context.recon_10m.ge(20),
        "R3": known & features.new_ip.eq(1) & features.off_hours.eq(1),
        "R4": sensitive & (features.new_client.eq(1) | features.off_hours.eq(1)),
        "R5": known & context.compartments_10m.ge(4) & context.events_10m.ge(10),
    }
    ids = [[] for _ in range(len(df))]
    risk = np.zeros(len(df))
    for rule, mask in masks.items():
        for i in np.flatnonzero(mask):
            ids[i].append(rule)
            risk[i] = max(risk[i], RULES[rule][1])
    return pd.DataFrame({"rule_ids": [", ".join(x) for x in ids], "rule_score": risk})
