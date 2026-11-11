"""Bounded-dimensional features. Labels, scenarios and IDs never enter a model."""

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass

import numpy as np
import pandas as pd

FREQUENCY_FIELDS = ("event_name", "source_service", "auth_type", "opc_client_info")
RECON = {"GetVcn", "GetVnic", "ListBuckets", "ListUsers", "ListInstances"}


@dataclass
class Baseline:
    rows: int
    frequencies: dict
    principal_ips: dict
    principal_clients: dict
    principal_events: dict

    @classmethod
    def fit(cls, df):
        known = df[df.principal_name.ne("unknown")]

        def per_principal(field):
            return known.groupby("principal_name")[field].agg(set).to_dict()

        return cls(
            len(df),
            {c: df[c].value_counts().to_dict() for c in FREQUENCY_FIELDS},
            per_principal("ip_address"),
            per_principal("opc_client_info"),
            per_principal("event_name"),
        )


def context_features(df: pd.DataFrame, window_minutes: int = 10) -> pd.DataFrame:
    """Past/current events only, in [t-window, t]; no wall-clock dependency.

    State resets per batch. Equal timestamps use event_id order. Unknown principals
    are isolated so unrelated anonymous users cannot manufacture a shared burst.
    """
    result = np.zeros((len(df), 4), dtype=float)
    windows = defaultdict(deque)
    failures, recons = Counter(), Counter()
    compartments = defaultdict(Counter)
    ordered = df.assign(_position=np.arange(len(df))).sort_values(["event_time", "event_id"], kind="stable")
    span = pd.Timedelta(minutes=window_minutes)
    for row in ordered.itertuples(index=False, name=None):
        values = dict(zip(ordered.columns, row))
        t, p = values["event_time"], values["principal_name"]
        p = ("anonymous", values["event_id"]) if p == "unknown" else ("known", p)
        queue = windows[p]
        while queue and queue[0][0] < t - span:
            _, failed, recon, compartment = queue.popleft()
            failures[p] -= failed
            recons[p] -= recon
            compartments[p][compartment] -= 1
            if not compartments[p][compartment]:
                del compartments[p][compartment]
        failed = int(values["response_status"] in (401, 403))
        recon = int(values["event_name"] in RECON)
        compartment = values["compartment_name"]
        queue.append((t, failed, recon, compartment))
        failures[p] += failed
        recons[p] += recon
        compartments[p][compartment] += 1
        distinct = len(compartments[p]) - int("unknown" in compartments[p])
        result[values["_position"]] = (len(queue), failures[p], recons[p], distinct)
    return pd.DataFrame(result, columns=["events_10m", "failures_10m", "recon_10m", "compartments_10m"])


def build_features(df: pd.DataFrame, baseline: Baseline) -> tuple[pd.DataFrame, pd.DataFrame]:
    context = context_features(df)
    hour = df.event_time.dt.hour + df.event_time.dt.minute / 60
    features = pd.DataFrame(
        {
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "weekend": (df.event_time.dt.dayofweek >= 5).astype(float),
            "off_hours": ((hour < 7) | (hour >= 20)).astype(float),
            "http_error": (df.response_status >= 400).astype(float),
            "auth_failure": df.response_status.isin([401, 403]).astype(float),
        }
    )
    for col in context:
        features["log_" + col] = np.log1p(context[col])
    for col, counts in baseline.frequencies.items():
        denominator = baseline.rows + len(counts) + 1
        features[col + "_surprisal"] = df[col].map(lambda x: -math.log((counts.get(x, 0) + 1) / denominator))
    features["new_principal"] = (~df.principal_name.isin(baseline.principal_ips)).astype(float)
    for col, mapping, name in [
        ("ip_address", baseline.principal_ips, "new_ip"),
        ("opc_client_info", baseline.principal_clients, "new_client"),
        ("event_name", baseline.principal_events, "new_action"),
    ]:
        features[name] = [
            float(p in mapping and value != "unknown" and value not in mapping[p])
            for p, value in zip(df.principal_name, df[col])
        ]
    return features.astype(float), context
