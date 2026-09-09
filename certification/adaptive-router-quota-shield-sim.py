from dataclasses import dataclass, replace
from typing import List, Optional

FREE_VERIFIED = "FREE_VERIFIED"
UNKNOWN = "UNKNOWN"
PAID = "PAID"

@dataclass(frozen=True)
class Route:
    name: str
    provider: str
    cost_class: str
    functional: bool
    security_allowed: bool
    supports_task: bool
    heavy_local: bool
    quality_fit: float
    task_specialization: float
    recent_success: float
    diversity_bonus: float
    free_capacity: float
    historical_reliability: float
    latency_penalty: float
    quota_pressure: float
    security_risk: float
    correlated_failure_risk: float
    remaining_tokens: int
    reserved_tokens: int = 0
    circuit_open: bool = False

def hard_filter(route: Route) -> bool:
    return (
        route.cost_class == FREE_VERIFIED
        and route.functional
        and route.security_allowed
        and route.supports_task
        and not route.heavy_local
        and not route.circuit_open
    )

def score(route: Route) -> float:
    return (
        route.quality_fit
        + route.task_specialization
        + route.recent_success
        + route.diversity_bonus
        + route.free_capacity
        + route.historical_reliability
        - route.latency_penalty
        - route.quota_pressure
        - route.security_risk
        - route.correlated_failure_risk
    )

def reserve(route: Route, required_tokens: int, emergency_reserve: int) -> Optional[Route]:
    available = route.remaining_tokens - route.reserved_tokens
    if available < required_tokens + emergency_reserve:
        return None
    return replace(route, reserved_tokens=route.reserved_tokens + required_tokens)

def choose_route(routes: List[Route], required_tokens: int, emergency_reserve: int) -> Optional[Route]:
    candidates = []
    for route in routes:
        if not hard_filter(route):
            continue
        reserved = reserve(route, required_tokens, emergency_reserve)
        if reserved is not None:
            candidates.append(reserved)
    if not candidates:
        return None
    return max(candidates, key=score)

def simulate_failover(routes: List[Route], failed_provider: str, required_tokens: int, emergency_reserve: int):
    degraded = [
        replace(r, functional=False, circuit_open=True)
        if r.provider == failed_provider else r
        for r in routes
    ]
    selected = choose_route(degraded, required_tokens, emergency_reserve)
    return {
        "failed_provider": failed_provider,
        "selected_route": selected.name if selected else None,
        "selected_provider": selected.provider if selected else None,
        "selected_score": round(score(selected), 4) if selected else None,
        "zero_spend": bool(selected and selected.cost_class == FREE_VERIFIED),
        "heavy_local": bool(selected and selected.heavy_local),
    }

def demo_routes() -> List[Route]:
    return [
        Route("github-free", "github", FREE_VERIFIED, True, True, True, False,
              9.2, 9.0, 9.3, 0.4, 8.8, 9.4, 0.8, 1.0, 0.2, 0.5, 120000),
        Route("gitlab-free", "gitlab", FREE_VERIFIED, True, True, True, False,
              8.9, 8.7, 9.1, 1.0, 8.2, 9.0, 0.7, 0.5, 0.2, 0.3, 100000),
        Route("local-heavy", "local", FREE_VERIFIED, True, True, True, True,
              10.0, 10.0, 10.0, 0.0, 10.0, 10.0, 0.0, 0.0, 0.0, 0.0, 999999),
        Route("unknown-cloud", "unknown", UNKNOWN, True, True, True, False,
              10.0, 10.0, 10.0, 1.0, 10.0, 10.0, 0.1, 0.0, 0.0, 0.0, 999999),
    ]

if __name__ == "__main__":
    routes = demo_routes()
    selected = choose_route(routes, required_tokens=20000, emergency_reserve=10000)
    print({
        "normal_selected": selected.name if selected else None,
        "normal_score": round(score(selected), 4) if selected else None,
        "failover": simulate_failover(routes, "github", 20000, 10000),
    })
