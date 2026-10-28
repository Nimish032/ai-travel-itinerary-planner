"""Pure-Python geographic clustering and route optimization."""

from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

from core.models import Activity

Coordinate = Tuple[float, float]


def haversine_km(first: Coordinate, second: Coordinate) -> float:
    """Return great-circle distance between two latitude/longitude points."""

    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(a))


def route_distance(points: Sequence[Coordinate]) -> float:
    return sum(haversine_km(points[index], points[index + 1]) for index in range(len(points) - 1))


def _nearest_centroid(item: Activity, centroids: Sequence[Coordinate]) -> int:
    point = (item.lat, item.lon)
    return min(range(len(centroids)), key=lambda index: haversine_km(point, centroids[index]))


def cluster_activities(
    activities: Sequence[Activity],
    days: int,
    seed: int = 42,
) -> List[List[Activity]]:
    """Cluster activities deterministically and keep every cluster non-empty."""

    if not activities:
        return [[] for _ in range(max(1, days))]
    k = max(1, min(days, len(activities)))
    rng = random.Random(seed)
    centroids: List[Coordinate] = [(activities[rng.randrange(len(activities))].lat,
                                    activities[rng.randrange(len(activities))].lon)]
    while len(centroids) < k:
        distances = [
            min(haversine_km((item.lat, item.lon), center) ** 2 for center in centroids)
            for item in activities
        ]
        total = sum(distances)
        if total == 0:
            centroids.append((activities[len(centroids) % len(activities)].lat,
                              activities[len(centroids) % len(activities)].lon))
        else:
            pick = rng.random() * total
            for index, distance in enumerate(distances):
                pick -= distance
                if pick <= 0:
                    centroids.append((activities[index].lat, activities[index].lon))
                    break
    assignments = [_nearest_centroid(item, centroids) for item in activities]
    for _ in range(12):
        groups = [[item for item, group in zip(activities, assignments) if group == index]
                  for index in range(k)]
        for index, group in enumerate(groups):
            if group:
                centroids[index] = (
                    sum(item.lat for item in group) / len(group),
                    sum(item.lon for item in group) / len(group),
                )
        new_assignments = [_nearest_centroid(item, centroids) for item in activities]
        if new_assignments == assignments:
            break
        assignments = new_assignments

    # Ensure no empty groups by moving the farthest item from an oversized group.
    groups = [[item for item, group in zip(activities, assignments) if group == index]
              for index in range(k)]
    for empty_index, group in enumerate(groups):
        if group:
            continue
        donor_index = max(range(k), key=lambda idx: len(groups[idx]))
        if not groups[donor_index]:
            continue
        moved = groups[donor_index].pop()
        groups[empty_index].append(moved)
    return groups


def two_opt(route: Sequence[Activity]) -> List[Activity]:
    """Improve a route using deterministic 2-opt swaps."""

    best = list(route)
    if len(best) < 4:
        return best
    improved = True
    while improved:
        improved = False
        best_distance = route_distance([(item.lat, item.lon) for item in best])
        for first in range(1, len(best) - 2):
            for second in range(first + 1, len(best)):
                candidate = best[:first] + list(reversed(best[first:second])) + best[second:]
                distance = route_distance([(item.lat, item.lon) for item in candidate])
                if distance + 1e-9 < best_distance:
                    best, best_distance, improved = candidate, distance, True
        if not improved:
            break
    return best


def order_route(activities: Sequence[Activity], start: Coordinate) -> List[Activity]:
    """Order stops with nearest-neighbor followed by 2-opt."""

    remaining = list(activities)
    ordered: List[Activity] = []
    current = start
    while remaining:
        next_item = min(remaining, key=lambda item: haversine_km(current, (item.lat, item.lon)))
        ordered.append(next_item)
        remaining.remove(next_item)
        current = (next_item.lat, next_item.lon)
    return two_opt(ordered)


def order_clusters(groups: Sequence[Sequence[Activity]], hub: Coordinate) -> List[List[Activity]]:
    """Order day clusters by their nearest hub/previous-cluster approach."""

    remaining = [list(group) for group in groups if group]
    ordered: List[List[Activity]] = []
    current = hub
    while remaining:
        group = min(
            remaining,
            key=lambda candidate: min(
                haversine_km(current, (item.lat, item.lon)) for item in candidate
            ),
        )
        remaining.remove(group)
        ordered.append(order_route(group, current))
        current = (ordered[-1][-1].lat, ordered[-1][-1].lon)
    return ordered


def transit_minutes(route: Sequence[Activity], hub: Coordinate) -> Tuple[int, float]:
    """Estimate urban transit with a 25 km/h average and a 10 minute buffer."""

    points = [hub] + [(item.lat, item.lon) for item in route]
    distance = route_distance(points)
    minutes = int(round(distance / 25 * 60 + (10 if route else 0)))
    return minutes, distance
