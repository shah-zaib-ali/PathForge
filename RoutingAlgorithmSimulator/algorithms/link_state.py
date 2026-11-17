"""
Link-State Routing Algorithm Implementation

Implements Dijkstra's shortest-path algorithm for link-state routing.
This is a from-scratch implementation, not just a NetworkX wrapper.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
import heapq
import time
from network.topology import NetworkTopology, Router, Link


@dataclass
class DijkstraStep:
    """Records a single step of Dijkstra's algorithm for educational display."""
    iteration: int
    current_node: Optional[str]
    visited: Set[str]
    tentative_distances: Dict[str, float]
    predecessors: Dict[str, Optional[str]]
    priority_queue: List[Tuple[float, str]]
    description: str


@dataclass
class LinkStateResult:
    """Results of link-state routing computation."""
    source_router: str
    distances: Dict[str, float]
    next_hops: Dict[str, Optional[str]]
    paths: Dict[str, List[str]]
    steps: List[DijkstraStep]
    computation_time: float
    converged: bool
    
    def get_routing_table(self) -> List[Dict[str, Any]]:
        """Generate routing table as list of dictionaries for display."""
        table = []
        for dest in sorted(self.distances.keys()):
            if dest == self.source_router:
                continue
            dist = self.distances[dest]
            next_hop = self.next_hops.get(dest)
            path = self.paths.get(dest, [])
            table.append({
                'Destination': dest,
                'Next Hop': next_hop if next_hop else '—',
                'Cost': dist if dist != float('inf') else '∞',
                'Path': ' → '.join(path) if path else 'Unreachable'
            })
        return table


class LinkStateRouter:
    """
    Implements Link-State routing using Dijkstra's algorithm.
    Each router maintains a complete topology database and computes shortest paths independently.
    """
    
    def __init__(self, topology: NetworkTopology):
        self.topology = topology
        self.topology_database: Dict[str, Dict[str, float]] = {}
        self._build_topology_database()
    
    def _build_topology_database(self) -> None:
        """Build the link-state database from the topology."""
        self.topology_database = {}
        for router_id in self.topology.routers:
            self.topology_database[router_id] = {}
        
        for link in self.topology.get_active_links():
            # Add bidirectional link information
            self.topology_database[link.source][link.target] = link.cost
            self.topology_database[link.target][link.source] = link.cost
    
    def update_topology(self, topology: NetworkTopology) -> None:
        """Update the topology and rebuild database."""
        self.topology = topology
        self._build_topology_database()
    
    def compute_shortest_paths(self, source_id: str, 
                               record_steps: bool = True) -> LinkStateResult:
        """
        Compute shortest paths from source to all destinations using Dijkstra's algorithm.
        
        Args:
            source_id: Source router ID
            record_steps: Whether to record each step for educational purposes
            
        Returns:
            LinkStateResult with distances, next hops, paths, and optional step-by-step trace
        """
        start_time = time.perf_counter()
        
        # Initialize
        distances = {router_id: float('inf') for router_id in self.topology.routers}
        distances[source_id] = 0.0
        predecessors: Dict[str, Optional[str]] = {router_id: None for router_id in self.topology.routers}
        visited: Set[str] = set()
        
        # Priority queue: (distance, node)
        pq: List[Tuple[float, str]] = [(0.0, source_id)]
        
        steps: List[DijkstraStep] = []
        iteration = 0
        
        if record_steps:
            steps.append(DijkstraStep(
                iteration=0,
                current_node=None,
                visited=set(),
                tentative_distances=distances.copy(),
                predecessors=predecessors.copy(),
                priority_queue=pq.copy(),
                description=f"Initialize: distance to {source_id} = 0, all others = ∞"
            ))
        
        while pq:
            current_dist, current = heapq.heappop(pq)
            
            # Skip if already visited with a better distance
            if current in visited:
                continue
            
            if current_dist > distances[current]:
                continue
            
            visited.add(current)
            
            if record_steps:
                steps.append(DijkstraStep(
                    iteration=iteration + 1,
                    current_node=current,
                    visited=visited.copy(),
                    tentative_distances=distances.copy(),
                    predecessors=predecessors.copy(),
                    priority_queue=pq.copy(),
                    description=f"Visit {current} (distance={current_dist}). Relax neighbors."
                ))
            
            # Relax edges
            for neighbor, cost in self.topology.get_neighbors(current):
                if neighbor in visited:
                    continue
                
                new_dist = current_dist + cost
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    predecessors[neighbor] = current
                    heapq.heappush(pq, (new_dist, neighbor))
                    
                    if record_steps:
                        steps.append(DijkstraStep(
                            iteration=iteration + 1,
                            current_node=current,
                            visited=visited.copy(),
                            tentative_distances=distances.copy(),
                            predecessors=predecessors.copy(),
                            priority_queue=pq.copy(),
                            description=f"  Relax {current}→{neighbor}: new distance = {new_dist}"
                        ))
            
            iteration += 1
        
        # Build paths and next hops
        paths = {}
        next_hops = {}
        
        for dest_id in self.topology.routers:
            if dest_id == source_id:
                paths[dest_id] = [source_id]
                next_hops[dest_id] = source_id
            elif distances[dest_id] == float('inf'):
                paths[dest_id] = []
                next_hops[dest_id] = None
            else:
                # Reconstruct path
                path = []
                curr = dest_id
                while curr is not None:
                    path.append(curr)
                    curr = predecessors[curr]
                path.reverse()
                paths[dest_id] = path
                
                # Next hop is the first step after source
                if len(path) >= 2:
                    next_hops[dest_id] = path[1]
                else:
                    next_hops[dest_id] = None
        
        computation_time = time.perf_counter() - start_time
        
        if record_steps:
            steps.append(DijkstraStep(
                iteration=iteration + 1,
                current_node=None,
                visited=visited.copy(),
                tentative_distances=distances.copy(),
                predecessors=predecessors.copy(),
                priority_queue=[],
                description="Algorithm complete. All shortest paths computed."
            ))
        
        return LinkStateResult(
            source_router=source_id,
            distances=distances,
            next_hops=next_hops,
            paths=paths,
            steps=steps,
            computation_time=computation_time,
            converged=True
        )
    
    def get_shortest_path(self, source_id: str, dest_id: str) -> Optional[List[str]]:
        """Get shortest path between two specific routers."""
        result = self.compute_shortest_paths(source_id, record_steps=False)
        return result.paths.get(dest_id) if result.paths.get(dest_id) else None
    
    def get_distance(self, source_id: str, dest_id: str) -> Optional[float]:
        """Get shortest distance between two routers."""
        result = self.compute_shortest_paths(source_id, record_steps=False)
        dist = result.distances.get(dest_id)
        return dist if dist != float('inf') else None


def run_link_state_for_all_routers(topology: NetworkTopology, 
                                    record_steps: bool = False) -> Dict[str, LinkStateResult]:
    """
    Run link-state routing computation for all routers in the topology.
    
    Returns:
        Dictionary mapping router_id to LinkStateResult
    """
    router = LinkStateRouter(topology)
    results = {}
    
    for router_id in topology.routers:
        results[router_id] = router.compute_shortest_paths(router_id, record_steps=record_steps)
    
    return results


def simulate_lsa_flooding(topology: NetworkTopology) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Simulate Link-State Advertisement (LSA) flooding.
    In a real network, each router originates LSAs for its links and floods them.
    This simulates the process and returns the final topology database at each router.
    """
    # In link-state, every router ends up with identical topology database
    # This simulates the flooding process conceptually
    
    # Each router starts with its own link information
    lsa_database: Dict[str, Dict[str, Dict[str, float]]] = {}
    
    for router_id in topology.routers:
        lsa_database[router_id] = {}
        # Own links
        for neighbor, cost in topology.get_neighbors(router_id):
            lsa_database[router_id][neighbor] = {neighbor: cost}
    
    # Flooding simulation: iteratively share LSAs until convergence
    changed = True
    iterations = 0
    max_iterations = len(topology.routers) * 2  # Upper bound
    
    while changed and iterations < max_iterations:
        changed = False
        iterations += 1
        
        for router_id in topology.routers:
            # Get neighbors
            neighbors = [n for n, _ in topology.get_neighbors(router_id)]
            
            # Receive LSAs from neighbors
            for neighbor in neighbors:
                neighbor_lsas = lsa_database[neighbor]
                for origin, links in neighbor_lsas.items():
                    if origin not in lsa_database[router_id]:
                        lsa_database[router_id][origin] = links.copy()
                        changed = True
                    else:
                        # Merge link information
                        for link_dest, cost in links.items():
                            if link_dest not in lsa_database[router_id][origin]:
                                lsa_database[router_id][origin][link_dest] = cost
                                changed = True
    
    return lsa_database