"""Prometheus metrics (Plan.md §11.1), one registry per app so tests never share counters."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.ops = Counter(
            "mphone_op_total",
            "Ops run through the gateway",
            ["op", "ok", "error_code"],
            registry=self.registry,
        )
        self.op_seconds = Histogram(
            "mphone_op_duration_seconds",
            "Op latency at the gateway",
            ["op"],
            buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
            registry=self.registry,
        )
        self.nodes = Gauge("mphone_nodes_connected", "Nodes with a live connection", registry=self.registry)
        self.policy = Counter(
            "mphone_policy_decisions_total",
            "Policy decisions on policed ops",
            ["rule", "decision"],
            registry=self.registry,
        )
        self.leases = Counter(
            "mphone_lease_events_total", "Lease acquisitions and conflicts", ["event"], registry=self.registry
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)
