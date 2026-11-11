"""Seeded synthetic events; no original identities or log records are included."""

import numpy as np
import pandas as pd


def generate_demo(seed=42, days=30, events_per_day=240):
    if days < 10 or events_per_day < 20:
        raise ValueError("Use at least 10 days and 20 events per day.")
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-01-01", tz="UTC")
    rows = []
    actions = [
        "GetVcn",
        "GetVnic",
        "ListBuckets",
        "GetObject",
        "ListInstances",
        "UpdateInstance",
        "CreatePolicy",
    ]
    services = {
        "GetVcn": "network",
        "GetVnic": "network",
        "ListBuckets": "storage",
        "GetObject": "storage",
        "ListInstances": "compute",
        "UpdateInstance": "compute",
        "CreatePolicy": "identity",
    }

    def event(t, user, action, *, label=0, scenario="routine", **changes):
        row = {
            "event_time": t,
            "event_name": action,
            "principal_name": f"analyst-{user:02d}",
            "ip_address": f"192.0.2.{user + 10}",
            "source_service": services.get(action, "identity"),
            "auth_type": "api_key",
            "resource_name": f"demo-resource-{user % 8:02d}",
            "opc_client_info": "sdk-python/2.0",
            "compartment_name": f"team-{user % 3}",
            "response_status": 200,
            "label": label,
            "scenario": scenario,
            "is_synthetic": True,
        }
        row.update(changes)
        rows.append(row)

    for day in range(days):
        base = start + pd.Timedelta(days=day)
        for _ in range(events_per_day):
            user = int(rng.integers(0, 16))
            hour = int(rng.integers(8, 19)) if rng.random() > 0.08 else int(rng.integers(0, 24))
            t = base + pd.Timedelta(hours=hour, seconds=int(rng.integers(0, 3600)))
            action = str(rng.choice(actions, p=[0.18, 0.14, 0.16, 0.24, 0.16, 0.10, 0.02]))
            event(
                t,
                user,
                action,
                response_status=int(rng.choice([200, 401, 403, 500], p=[0.96, 0.015, 0.015, 0.01])),
            )
        # Legitimate scheduled work and failed logins make false positives observable.
        for j in range(8):
            event(
                base + pd.Timedelta(hours=2, seconds=j * 45),
                15,
                "ListInstances",
                scenario="scheduled_inventory",
            )
        if day >= int(days * 0.6):
            for j in range(5):
                event(
                    base + pd.Timedelta(hours=13, minutes=j),
                    7,
                    "GetObject",
                    scenario="benign_ip_change",
                    ip_address="198.51.100.77",
                )
        if day < int(days * 0.8):
            continue
        for j in range(16):
            event(
                base + pd.Timedelta(hours=9, seconds=j * 8),
                2,
                "AuthenticateUser",
                label=1,
                scenario="credential_abuse",
                response_status=401,
                ip_address="203.0.113.90",
                opc_client_info="custom-client/1.0",
            )
        for j in range(32):
            event(
                base + pd.Timedelta(hours=11, seconds=j * 5),
                4,
                str(rng.choice(["GetVcn", "GetVnic", "ListBuckets"])),
                label=1,
                scenario="reconnaissance_burst",
                compartment_name=f"team-{j % 6}",
            )
        for j in range(8):
            event(
                base + pd.Timedelta(hours=3, minutes=j),
                6,
                "CreatePolicy",
                label=1,
                scenario="unusual_policy_change",
                ip_address="203.0.113.42",
                opc_client_info="curl/8.0",
            )
        # Deliberately difficult: malicious labels with ordinary observable features.
        for j in range(6):
            event(
                base + pd.Timedelta(hours=15, minutes=j * 9),
                9,
                "GetObject",
                label=1,
                scenario="low_and_slow_access",
            )
    df = pd.DataFrame(rows).sort_values("event_time", kind="stable").reset_index(drop=True)
    df.insert(0, "event_id", [f"demo-{seed}-{i:07d}" for i in range(len(df))])
    return df
