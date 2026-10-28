"""Geographic clustering and route optimization tests."""

from core.clustering import (
    cluster_activities, haversine_km, order_route, route_distance, transit_minutes,
)
from core.models import Activity


def activity(name, lat, lon):
    return Activity(name=name, category="Test", lat=lat, lon=lon)


def test_haversine_is_zero_for_same_point_and_positive_for_different_points():
    assert haversine_km((0, 0), (0, 0)) == 0
    assert 110 < haversine_km((0, 0), (1, 0)) < 112


def test_balanced_clusters_assign_every_activity_once():
    activities = [
        activity("a", 48.85, 2.30), activity("b", 48.86, 2.31),
        activity("c", 48.90, 2.35), activity("d", 48.91, 2.36),
        activity("e", 48.80, 2.25), activity("f", 48.81, 2.26),
    ]
    groups = cluster_activities(activities, 3)
    assert all(groups)
    assert {item.name for group in groups for item in group} == {item.name for item in activities}


def test_nearest_neighbor_route_is_shorter_than_random_order():
    points = [activity(str(i), 0, i) for i in [0, 3, 1, 4, 2]]
    ordered = order_route(points, (0, 0))
    assert route_distance([(item.lat, item.lon) for item in ordered]) <= route_distance(
        [(item.lat, item.lon) for item in points]
    )


def test_transit_estimate_has_buffer():
    route = [activity("a", 0, 0.1)]
    minutes, distance = transit_minutes(route, (0, 0))
    assert distance > 0
    assert minutes >= 10
