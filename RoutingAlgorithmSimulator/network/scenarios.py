"""
Predefined Network Scenarios

Provides a collection of predefined network topologies for demonstration and testing.
"""

from network.topology import NetworkTopology, create_predefined_scenario, create_random_topology


SCENARIOS = {
    "simple_three": {
        "name": "Simple Three-Router Network",
        "description": "Basic network with 3 routers forming a triangle. Shows basic routing behavior.",
        "router_count": 3,
        "link_count": 3
    },
    "multiple_paths": {
        "name": "Multiple Paths Network",
        "description": "Network with multiple alternative paths between endpoints. Demonstrates path selection.",
        "router_count": 5,
        "link_count": 7
    },
    "cost_vs_hops": {
        "name": "Cost vs Hop Count",
        "description": "Network where lowest-cost path has more hops than shortest-hop path. Illustrates metric differences.",
        "router_count": 4,
        "link_count": 4
    },
    "distance_vector_loop": {
        "name": "Distance Vector Loop Scenario",
        "description": "Classic topology for demonstrating count-to-infinity problem in Distance Vector routing.",
        "router_count": 3,
        "link_count": 3
    },
    "link_failure": {
        "name": "Link Failure Recovery",
        "description": "Network where primary path fails, forcing traffic onto backup path.",
        "router_count": 4,
        "link_count": 4
    },
    "disconnected": {
        "name": "Disconnected Network",
        "description": "Two separate network components with no connectivity between them.",
        "router_count": 4,
        "link_count": 2
    },
    "rip_example": {
        "name": "RIP Hop-Count Example",
        "description": "Shows how RIP (hop-count) may choose different path than cost-based routing.",
        "router_count": 4,
        "link_count": 5
    },
    "larger_network": {
        "name": "Larger Test Network (8 routers)",
        "description": "Larger network for performance comparison and convergence analysis.",
        "router_count": 8,
        "link_count": 14
    }
}


def get_scenario_info(scenario_key: str) -> dict:
    """Get information about a predefined scenario."""
    return SCENARIOS.get(scenario_key, {})


def list_scenarios() -> list:
    """List all available scenario keys."""
    return list(SCENARIOS.keys())


def load_scenario(scenario_key: str) -> NetworkTopology:
    """Load a predefined scenario by key."""
    return create_predefined_scenario(scenario_key)


def create_count_to_infinity_topology() -> NetworkTopology:
    """
    Create the classic 3-node topology for count-to-infinity demonstration.
    
    Topology:
    R1 --(1)-- R2 --(1)-- R3
    
    Initially all links up. Then R2-R3 link fails.
    R2 thinks it can reach R3 via R1 (cost 2), R1 thinks it can reach R3 via R2 (cost 2),
    leading to count-to-infinity.
    """
    return create_predefined_scenario("distance_vector_loop")


def create_ospf_validation_topology() -> NetworkTopology:
    """Create a topology suitable for OSPF validation testing."""
    topo = NetworkTopology()
    
    # Create a network with multiple areas conceptually
    routers = {}
    for i in range(1, 7):
        routers[i] = topo.add_router(f"R{i}")
    
    # Area 0 (backbone) - fully connected core
    topo.add_link(routers[1].id, routers[2].id, 10)
    topo.add_link(routers[2].id, routers[3].id, 10)
    topo.add_link(routers[1].id, routers[3].id, 15)
    
    # Area 1 connections
    topo.add_link(routers[1].id, routers[4].id, 5)
    topo.add_link(routers[2].id, routers[4].id, 5)
    
    # Area 2 connections
    topo.add_link(routers[3].id, routers[5].id, 5)
    topo.add_link(routers[3].id, routers[6].id, 5)
    topo.add_link(routers[5].id, routers[6].id, 10)
    
    return topo


def create_convergence_test_topology(size: int = 6) -> NetworkTopology:
    """Create a topology for convergence testing with specified size."""
    topo = NetworkTopology()
    
    routers = {}
    for i in range(1, size + 1):
        routers[i] = topo.add_router(f"R{i}")
    
    # Create a line topology for predictable convergence
    for i in range(1, size):
        topo.add_link(routers[i].id, routers[i+1].id, 1)
    
    # Add some cross links
    if size >= 4:
        topo.add_link(routers[1].id, routers[3].id, 3)
    if size >= 5:
        topo.add_link(routers[2].id, routers[4].id, 3)
    if size >= 6:
        topo.add_link(routers[3].id, routers[5].id, 3)
        topo.add_link(routers[1].id, routers[size].id, size * 2)
    
    return topo