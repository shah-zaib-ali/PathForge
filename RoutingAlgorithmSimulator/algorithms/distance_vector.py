"""
Distance-Vector Routing Algorithm Implementation

Implements iterative Bellman-Ford-style distance vector routing with
support for synchronous and asynchronous update modes.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy
import time
from network.topology import NetworkTopology


class UpdateStrategy(Enum):
    """Update strategy for distance vector algorithm."""
    SYNCHRONOUS = "synchronous"      # All routers update simultaneously each round
    ASYNCHRONOUS = "asynchronous"    # Routers update in random order


@dataclass
class DistanceVectorEntry:
    """A single entry in a router's distance vector."""
    destination: str
    distance: float
    next_hop: Optional[str]
    path: List[str] = field(default_factory=list)
    
    def __str__(self):
        if self.distance == float('inf'):
            return f"{self.destination}: ∞ (unreachable)"
        return f"{self.destination}: {self.distance} via {self.next_hop}"


@dataclass
class DistanceVectorTable:
    """Complete distance vector table for a router."""
    router_id: str
    entries: Dict[str, DistanceVectorEntry] = field(default_factory=dict)
    
    def get_entry(self, destination: str) -> DistanceVectorEntry:
        """Get entry for destination, creating if needed."""
        if destination not in self.entries:
            if destination == self.router_id:
                self.entries[destination] = DistanceVectorEntry(
                    destination=destination, distance=0.0, next_hop=destination, path=[destination]
                )
            else:
                self.entries[destination] = DistanceVectorEntry(
                    destination=destination, distance=float('inf'), next_hop=None, path=[]
                )
        return self.entries[destination]
    
    def update_entry(self, destination: str, distance: float, next_hop: Optional[str]) -> bool:
        """Update an entry. Returns True if changed."""
        entry = self.get_entry(destination)
        old_distance = entry.distance
        old_next_hop = entry.next_hop
        
        if distance < entry.distance or (distance == entry.distance and next_hop != old_next_hop):
            entry.distance = distance
            entry.next_hop = next_hop
            # Reconstruct path
            if next_hop and distance != float('inf'):
                # Path will be built by the algorithm
                pass
            return True
        return False
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries for display."""
        result = []
        for dest in sorted(self.entries.keys()):
            entry = self.entries[dest]
            if dest == self.router_id:
                continue
            result.append({
                'Destination': dest,
                'Next Hop': entry.next_hop if entry.next_hop else '—',
                'Distance': entry.distance if entry.distance != float('inf') else '∞',
                'Path': ' → '.join(entry.path) if entry.path else 'Unreachable'
            })
        return result


@dataclass
class DVIterationRecord:
    """Records state after one iteration of distance vector updates."""
    iteration: int
    tables: Dict[str, DistanceVectorTable]
    messages_sent: int
    changes: List[Tuple[str, str, float, float]]  # (router, dest, old_dist, new_dist)
    converged: bool


@dataclass
class DistanceVectorResult:
    """Complete results of distance vector simulation."""
    topology: NetworkTopology
    strategy: UpdateStrategy
    iterations: List[DVIterationRecord]
    final_tables: Dict[str, DistanceVectorTable]
    converged: bool
    total_iterations: int
    total_messages: int
    computation_time: float
    max_iterations_reached: bool = False


class DistanceVectorRouter:
    """
    Implements a single router running the Distance Vector algorithm.
    Maintains its own distance vector and exchanges with neighbors.
    """
    
    def __init__(self, router_id: str, topology: NetworkTopology):
        self.router_id = router_id
        self.topology = topology
        self.table = DistanceVectorTable(router_id)
        self._initialize_table()
    
    def _initialize_table(self) -> None:
        """Initialize distance vector with direct link costs."""
        # Distance to self is 0
        self.table.get_entry(self.router_id)
        
        # Direct neighbors
        for neighbor, cost in self.topology.get_neighbors(self.router_id):
            entry = self.table.get_entry(neighbor)
            entry.distance = cost
            entry.next_hop = neighbor
            entry.path = [self.router_id, neighbor]
        
        # All other destinations start as unreachable
        for other_id in self.topology.routers:
            if other_id != self.router_id:
                self.table.get_entry(other_id)
    
    def get_vector(self) -> Dict[str, float]:
        """Get this router's distance vector for sharing with neighbors."""
        return {dest: entry.distance for dest, entry in self.table.entries.items()}
    
    def receive_vector(self, from_neighbor: str, neighbor_vector: Dict[str, float]) -> List[Tuple[str, float, float]]:
        """
        Process a received distance vector from a neighbor.
        Returns list of (destination, old_distance, new_distance) for changed entries.
        """
        changes = []
        link_cost = self.topology.get_link_cost(self.router_id, from_neighbor)
        
        if link_cost is None:
            return changes  # Link failed or doesn't exist
        
        for dest, neighbor_dist in neighbor_vector.items():
            if dest == self.router_id:
                continue  # Don't update distance to self
            
            # Bellman-Ford equation: D_x(y) = min_v [c(x,v) + D_v(y)]
            new_distance = link_cost + neighbor_dist
            
            # Only consider if neighbor has a valid path
            if neighbor_dist == float('inf'):
                continue
            
            entry = self.table.get_entry(dest)
            old_distance = entry.distance
            
            if new_distance < old_distance:
                entry.distance = new_distance
                entry.next_hop = from_neighbor
                changes.append((dest, old_distance, new_distance))
            elif new_distance == old_distance and entry.next_hop != from_neighbor:
                # Tie-breaking: could implement various strategies
                pass
        
        return changes
    
    def rebuild_paths(self, all_tables: Dict[str, 'DistanceVectorRouter']) -> None:
        """Rebuild path information from next-hop pointers."""
        for dest, entry in self.table.entries.items():
            if dest == self.router_id:
                entry.path = [self.router_id]
            elif entry.next_hop and entry.distance != float('inf'):
                # Follow next hops to build path
                path = [self.router_id]
                current = entry.next_hop
                visited = {self.router_id}
                
                while current and current != dest and current not in visited:
                    path.append(current)
                    visited.add(current)
                    if current in all_tables:
                        next_entry = all_tables[current].table.get_entry(dest)
                        current = next_entry.next_hop
                    else:
                        break
                
                if current == dest:
                    path.append(dest)
                entry.path = path
            else:
                entry.path = []


class DistanceVectorSimulator:
    """
    Simulates the Distance Vector routing protocol across a network topology.
    Supports both synchronous and asynchronous update modes.
    """
    
    def __init__(self, topology: NetworkTopology, 
                 strategy: UpdateStrategy = UpdateStrategy.SYNCHRONOUS,
                 max_iterations: int = 100,
                 infinity: float = float('inf')):
        self.topology = topology
        self.strategy = strategy
        self.max_iterations = max_iterations
        self.infinity = infinity
        
        # Create router instances
        self.routers: Dict[str, DistanceVectorRouter] = {}
        for router_id in topology.routers:
            self.routers[router_id] = DistanceVectorRouter(router_id, topology)
    
    def run(self, record_history: bool = True) -> DistanceVectorResult:
        """
        Run the distance vector simulation until convergence or max iterations.
        
        Args:
            record_history: Whether to record iteration history for visualization
            
        Returns:
            DistanceVectorResult with complete simulation history
        """
        start_time = time.perf_counter()
        iterations: List[DVIterationRecord] = []
        total_messages = 0
        
        # Record initial state
        if record_history:
            initial_tables = {rid: deepcopy(router.table) for rid, router in self.routers.items()}
            iterations.append(DVIterationRecord(
                iteration=0,
                tables=initial_tables,
                messages_sent=0,
                changes=[],
                converged=False
            ))
        
        converged = False
        
        for iteration in range(1, self.max_iterations + 1):
            all_changes = []
            iteration_messages = 0
            
            if self.strategy == UpdateStrategy.SYNCHRONOUS:
                # Phase 1: All routers send their vectors to neighbors
                vectors_to_send = {}
                for router_id, router in self.routers.items():
                    vectors_to_send[router_id] = router.get_vector()
                
                # Phase 2: All routers receive and process vectors
                for router_id, router in self.routers.items():
                    neighbors = [n for n, _ in self.topology.get_neighbors(router_id)]
                    for neighbor in neighbors:
                        neighbor_vector = vectors_to_send[neighbor]
                        changes = router.receive_vector(neighbor, neighbor_vector)
                        all_changes.extend([(router_id, dest, old, new) for dest, old, new in changes])
                        iteration_messages += 1
                
            else:  # ASYNCHRONOUS
                # Process routers in random order
                import random
                router_ids = list(self.routers.keys())
                random.shuffle(router_ids)
                
                for router_id in router_ids:
                    router = self.routers[router_id]
                    neighbors = [n for n, _ in self.topology.get_neighbors(router_id)]
                    for neighbor in neighbors:
                        neighbor_vector = self.routers[neighbor].get_vector()
                        changes = router.receive_vector(neighbor, neighbor_vector)
                        all_changes.extend([(router_id, dest, old, new) for dest, old, new in changes])
                        iteration_messages += 1
            
            # Rebuild paths after all updates
            for router in self.routers.values():
                router.rebuild_paths(self.routers)
            
            total_messages += iteration_messages
            
            # Check convergence
            converged = len(all_changes) == 0
            
            if record_history:
                current_tables = {rid: deepcopy(router.table) for rid, router in self.routers.items()}
                iterations.append(DVIterationRecord(
                    iteration=iteration,
                    tables=current_tables,
                    messages_sent=iteration_messages,
                    changes=all_changes,
                    converged=converged
                ))
            
            if converged:
                break
        
        # Final path rebuild
        for router in self.routers.values():
            router.rebuild_paths(self.routers)
        
        final_tables = {rid: router.table for rid, router in self.routers.items()}
        computation_time = time.perf_counter() - start_time
        max_iterations_reached = not converged and iteration >= self.max_iterations
        
        return DistanceVectorResult(
            topology=self.topology,
            strategy=self.strategy,
            iterations=iterations,
            final_tables=final_tables,
            converged=converged,
            total_iterations=iteration,
            total_messages=total_messages,
            computation_time=computation_time,
            max_iterations_reached=max_iterations_reached
        )
    
    def get_routing_table(self, router_id: str) -> List[Dict[str, Any]]:
        """Get routing table for a specific router."""
        if router_id in self.routers:
            return self.routers[router_id].table.to_dict_list()
        return []


def run_distance_vector(topology: NetworkTopology,
                        strategy: UpdateStrategy = UpdateStrategy.SYNCHRONOUS,
                        max_iterations: int = 100,
                        record_history: bool = True) -> DistanceVectorResult:
    """
    Convenience function to run distance vector simulation.
    
    Args:
        topology: Network topology
        strategy: Update strategy (synchronous or asynchronous)
        max_iterations: Maximum iterations before giving up
        record_history: Whether to record iteration history
        
    Returns:
        DistanceVectorResult with simulation results
    """
    simulator = DistanceVectorSimulator(topology, strategy, max_iterations)
    return simulator.run(record_history=record_history)


def compare_strategies(topology: NetworkTopology) -> Dict[str, DistanceVectorResult]:
    """Run both synchronous and asynchronous strategies for comparison."""
    results = {}
    for strategy in UpdateStrategy:
        results[strategy.value] = run_distance_vector(topology, strategy)
    return results