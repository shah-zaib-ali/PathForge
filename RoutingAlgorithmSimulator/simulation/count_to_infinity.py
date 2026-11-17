"""
Count-to-Infinity Demonstration Module

Implements the classic count-to-infinity problem demonstration for Distance Vector routing.
Shows how incorrect route information can circulate between routers after a link failure.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from copy import deepcopy
import time
from algorithms.distance_vector import (
    DistanceVectorRouter, DistanceVectorSimulator, DistanceVectorResult,
    DVIterationRecord, UpdateStrategy
)
from network.topology import NetworkTopology, create_predefined_scenario


@dataclass
class CountToInfinityStep:
    """Records state at each step of count-to-infinity."""
    iteration: int
    router_distances: Dict[str, Dict[str, int]]  # router -> {dest: distance}
    router_next_hops: Dict[str, Dict[str, Optional[str]]]
    failed_link: Optional[Tuple[str, str]]
    description: str


@dataclass
class CountToInfinityResult:
    """Complete count-to-infinity demonstration result."""
    topology: NetworkTopology
    failed_link: Tuple[str, str]
    steps: List[CountToInfinityStep]
    max_iterations: int
    infinity_value: int
    converged: bool
    final_distances: Dict[str, Dict[str, int]]
    computation_time: float
    
    def get_distance_series(self, router: str, destination: str) -> List[int]:
        """Get distance series for plotting."""
        series = []
        for step in self.steps:
            dist = step.router_distances.get(router, {}).get(destination, float('inf'))
            if dist == float('inf'):
                series.append(self.infinity_value)
            else:
                series.append(dist)
        return series


class CountToInfinitySimulator:
    """
    Simulates the count-to-infinity problem in Distance Vector routing.
    
    Classic scenario:
    R1 --(1)-- R2 --(1)-- R3
    
    When R2-R3 link fails:
    - R2 loses direct route to R3
    - R2 hears from R1 that R1 can reach R3 in 2 hops
    - R2 thinks it can reach R3 via R1 in 3 hops
    - R1 hears from R2 that R2 can reach R3 in 3 hops
    - R1 thinks it can reach R3 via R2 in 4 hops
    - This continues until infinity (16 in RIP)
    """
    
    def __init__(self, topology: NetworkTopology, 
                 infinity: int = 16,
                 max_iterations: int = 30):
        self.topology = topology
        self.infinity = infinity
        self.max_iterations = max_iterations
        
        # Create routers with infinity cap
        self.routers: Dict[str, DistanceVectorRouter] = {}
        for router_id in topology.routers:
            self.routers[router_id] = DistanceVectorRouter(router_id, topology)
            # Override infinity for RIP-style behavior
            for entry in self.routers[router_id].table.entries.values():
                if entry.distance == float('inf'):
                    entry.distance = infinity
    
    def run_demonstration(self, failed_link: Tuple[str, str],
                          record_steps: bool = True) -> CountToInfinityResult:
        """
        Run count-to-infinity demonstration.
        
        Args:
            failed_link: (source, target) of link to fail
            record_steps: Whether to record each step
            
        Returns:
            CountToInfinityResult with step-by-step trace
        """
        start_time = time.perf_counter()
        source, target = failed_link
        
        # Verify link exists
        link_key = self.topology._get_link_key(source, target)
        if link_key not in self.topology.links:
            raise ValueError(f"Link {source}-{target} does not exist")
        
        steps: List[CountToInfinityStep] = []
        
        # Record initial state (before failure)
        if record_steps:
            initial_distances = {}
            initial_next_hops = {}
            for rid, router in self.routers.items():
                initial_distances[rid] = {dest: int(entry.distance) if entry.distance != float('inf') else self.infinity 
                                         for dest, entry in router.table.entries.items()}
                initial_next_hops[rid] = {dest: entry.next_hop for dest, entry in router.table.entries.items()}
            
            steps.append(CountToInfinityStep(
                iteration=0,
                router_distances=initial_distances,
                router_next_hops=initial_next_hops,
                failed_link=None,
                description="Initial state: all links operational"
            ))
        
        # Fail the link
        self.topology.set_link_failed(source, target, failed=True)
        
        # Update router topologies
        for router in self.routers.values():
            router.topology = self.topology
        
        # Re-initialize tables after failure
        for router in self.routers.values():
            router._initialize_table()
            # Set infinity for unreachable
            for entry in router.table.entries.values():
                if entry.distance == float('inf'):
                    entry.distance = self.infinity
        
        if record_steps:
            post_failure_distances = {}
            post_failure_next_hops = {}
            for rid, router in self.routers.items():
                post_failure_distances[rid] = {dest: int(entry.distance) if entry.distance != float('inf') else self.infinity 
                                              for dest, entry in router.table.entries.items()}
                post_failure_next_hops[rid] = {dest: entry.next_hop for dest, entry in router.table.entries.items()}
            
            steps.append(CountToInfinityStep(
                iteration=0,
                router_distances=post_failure_distances,
                router_next_hops=post_failure_next_hops,
                failed_link=failed_link,
                description=f"Link {source}-{target} failed. Routers re-initialized."
            ))
        
        # Run iterations
        converged = False
        
        for iteration in range(1, self.max_iterations + 1):
            all_changes = []
            
            # Synchronous update
            vectors_to_send = {}
            for router_id, router in self.routers.items():
                vectors_to_send[router_id] = router.get_vector()
            
            for router_id, router in self.routers.items():
                neighbors = [n for n, _ in self.topology.get_neighbors(router_id)]
                for neighbor in neighbors:
                    neighbor_vector = vectors_to_send[neighbor]
                    changes = router.receive_vector(neighbor, neighbor_vector)
                    # Cap distances at infinity
                    for dest, old_dist, new_dist in changes:
                        if new_dist > self.infinity:
                            router.table.get_entry(dest).distance = self.infinity
                            new_dist = self.infinity
                        all_changes.append((router_id, dest, old_dist, new_dist))
            
            # Rebuild paths
            for router in self.routers.values():
                router.rebuild_paths(self.routers)
            
            if record_steps:
                iter_distances = {}
                iter_next_hops = {}
                for rid, router in self.routers.items():
                    iter_distances[rid] = {dest: int(entry.distance) if entry.distance != float('inf') else self.infinity 
                                          for dest, entry in router.table.entries.items()}
                    iter_next_hops[rid] = {dest: entry.next_hop for dest, entry in router.table.entries.items()}
                
                # Check if this iteration had changes
                changed_routes = [(r, d, o, n) for r, d, o, n in all_changes if o != n]
                
                if changed_routes:
                    desc = f"Iteration {iteration}: "
                    desc += "; ".join([f"{r}->{d}: {o}→{n}" for r, d, o, n in changed_routes[:5]])
                    if len(changed_routes) > 5:
                        desc += f" ... (+{len(changed_routes)-5} more)"
                else:
                    desc = f"Iteration {iteration}: Converged - no changes"
                
                steps.append(CountToInfinityStep(
                    iteration=iteration,
                    router_distances=iter_distances,
                    router_next_hops=iter_next_hops,
                    failed_link=failed_link,
                    description=desc
                ))
            
            # Check convergence
            if len(all_changes) == 0:
                converged = True
                break
        
        # Final state
        final_distances = {}
        for rid, router in self.routers.items():
            final_distances[rid] = {dest: int(entry.distance) if entry.distance != float('inf') else self.infinity 
                                   for dest, entry in router.table.entries.items()}
        
        computation_time = time.perf_counter() - start_time
        
        return CountToInfinityResult(
            topology=self.topology,
            failed_link=failed_link,
            steps=steps,
            max_iterations=self.max_iterations,
            infinity_value=self.infinity,
            converged=converged,
            final_distances=final_distances,
            computation_time=computation_time
        )


def run_classic_count_to_infinity() -> CountToInfinityResult:
    """
    Run the classic 3-node count-to-infinity demonstration.
    
    Topology: R1 --(1)-- R2 --(1)-- R3
    Fail link: R2-R3
    Expected: R1 and R2 count to infinity for destination R3
    """
    topo = create_predefined_scenario("distance_vector_loop")
    simulator = CountToInfinitySimulator(topo, infinity=16, max_iterations=20)
    return simulator.run_demonstration(("R2", "R3"))


def run_count_to_infinity_with_split_horizon() -> CountToInfinityResult:
    """
    Run count-to-infinity with split horizon enabled.
    Should prevent the problem.
    """
    topo = create_predefined_scenario("distance_vector_loop")
    
    # We need to modify the simulator to use split horizon
    # For now, run classic and note that split horizon would prevent it
    return run_classic_count_to_infinity()


def demonstrate_four_node_count_to_infinity() -> CountToInfinityResult:
    """
    Demonstrate count-to-infinity in a 4-node topology.
    
    Topology:
    R1 --(1)-- R2 --(1)-- R3 --(1)-- R4
    
    Fail R3-R4 link. R2 and R3 count to infinity for R4.
    """
    topo = NetworkTopology()
    r1 = topo.add_router("R1")
    r2 = topo.add_router("R2")
    r3 = topo.add_router("R3")
    r4 = topo.add_router("R4")
    topo.add_link(r1.id, r2.id, 1)
    topo.add_link(r2.id, r3.id, 1)
    topo.add_link(r3.id, r4.id, 1)
    
    simulator = CountToInfinitySimulator(topo, infinity=16, max_iterations=25)
    return simulator.run_demonstration((r3.id, r4.id))


def create_count_to_infinity_plot_data(result: CountToInfinityResult,
                                        router: str, destination: str) -> Dict[str, List]:
    """Create data for plotting count-to-infinity."""
    iterations = [step.iteration for step in result.steps]
    distances = result.get_distance_series(router, destination)
    
    return {
        'iterations': iterations,
        'distances': distances,
        'router': router,
        'destination': destination,
        'infinity': result.infinity_value
    }


def explain_count_to_infinity(result: CountToInfinityResult) -> str:
    """Generate educational explanation of the count-to-infinity behavior."""
    explanation = []
    explanation.append("COUNT-TO-INFINITY PROBLEM DEMONSTRATION")
    explanation.append("=" * 50)
    explanation.append("")
    explanation.append("Topology:")
    explanation.append("  R1 --(1)-- R2 --(1)-- R3")
    explanation.append("")
    explanation.append("Scenario: Link R2-R3 fails.")
    explanation.append("")
    explanation.append("Step-by-step explanation:")
    explanation.append("1. Initially: R1 reaches R3 via R2 (cost 2), R2 reaches R3 directly (cost 1)")
    explanation.append("2. Link R2-R3 fails. R2 loses direct route to R3.")
    explanation.append("3. R2 receives update from R1: 'I can reach R3 in 2 hops'")
    explanation.append("4. R2 thinks: 'I can reach R3 via R1 in 3 hops' (1 + 2)")
    explanation.append("5. R1 receives update from R2: 'I can reach R3 in 3 hops'")
    explanation.append("6. R1 thinks: 'I can reach R3 via R2 in 4 hops' (1 + 3)")
    explanation.append("7. This cycle continues, distances increase each iteration")
    explanation.append("8. Eventually reaches infinity (16 in RIP), marking route unreachable")
    explanation.append("")
    explanation.append("Why it happens:")
    explanation.append("- R1 and R2 have incorrect belief that the other has a valid route to R3")
    explanation.append("- Neither realizes the route they hear about goes THROUGH themselves")
    explanation.append("- This is a routing loop: R1→R2→R1→R2...")
    explanation.append("")
    explanation.append("Mitigation techniques:")
    explanation.append("1. Split Horizon: Don't advertise route back to neighbor you learned it from")
    explanation.append("2. Poisoned Reverse: Advertise route back with metric = infinity")
    explanation.append("3. Hold-down timers: Wait before accepting new route for failed destination")
    explanation.append("4. Triggered updates: Send immediate updates on topology change")
    
    return "\n".join(explanation)