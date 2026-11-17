"""
RIP (Routing Information Protocol) Simulation

Implements RIP-style distance vector routing with hop-count metric,
maximum hop count of 15, and metric 16 as infinity.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from copy import deepcopy
import time
from algorithms.distance_vector import (
    DistanceVectorRouter, DistanceVectorSimulator, DistanceVectorResult,
    DistanceVectorTable, DVIterationRecord, UpdateStrategy
)
from network.topology import NetworkTopology


# RIP Constants
RIP_INFINITY = 16
RIP_MAX_HOPS = 15


@dataclass
class RIPEntry:
    """RIP routing table entry with hop count metric."""
    destination: str
    hops: int
    next_hop: Optional[str]
    path: List[str] = field(default_factory=list)
    is_garbage: bool = False  # For route expiration simulation
    
    def is_reachable(self) -> bool:
        return self.hops < RIP_INFINITY
    
    def __str__(self):
        if not self.is_reachable():
            return f"{self.destination}: unreachable (16)"
        return f"{self.destination}: {self.hops} hops via {self.next_hop}"


@dataclass
class RIPTable:
    """RIP routing table for a router."""
    router_id: str
    entries: Dict[str, RIPEntry] = field(default_factory=dict)
    
    def get_entry(self, destination: str) -> RIPEntry:
        if destination not in self.entries:
            if destination == self.router_id:
                self.entries[destination] = RIPEntry(
                    destination=destination, hops=0, next_hop=destination, path=[destination]
                )
            else:
                self.entries[destination] = RIPEntry(
                    destination=destination, hops=RIP_INFINITY, next_hop=None, path=[]
                )
        return self.entries[destination]
    
    def update_entry(self, destination: str, hops: int, next_hop: Optional[str]) -> bool:
        """Update entry with new hop count. Returns True if changed."""
        entry = self.get_entry(destination)
        old_hops = entry.hops
        
        if hops < entry.hops or (hops == entry.hops and next_hop != entry.next_hop):
            entry.hops = min(hops, RIP_INFINITY)
            entry.next_hop = next_hop
            entry.is_garbage = (hops >= RIP_INFINITY)
            return True
        return False
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert to displayable format."""
        result = []
        for dest in sorted(self.entries.keys()):
            entry = self.entries[dest]
            if dest == self.router_id:
                continue
            result.append({
                'Destination': dest,
                'Next Hop': entry.next_hop if entry.next_hop else '—',
                'Hops': entry.hops if entry.is_reachable() else '16 (∞)',
                'Status': 'Valid' if entry.is_reachable() else 'Unreachable',
                'Path': ' → '.join(entry.path) if entry.path else '—'
            })
        return result


class RIPRouter(DistanceVectorRouter):
    """RIP-specific router using hop-count metric."""
    
    def __init__(self, router_id: str, topology: NetworkTopology):
        super().__init__(router_id, topology)
        # Convert base table to RIP table
        self.rip_table = RIPTable(router_id)
        self._initialize_rip_table()
    
    def _initialize_rip_table(self) -> None:
        """Initialize RIP table with direct connections (1 hop each)."""
        self.rip_table.get_entry(self.router_id)
        
        for neighbor, _ in self.topology.get_neighbors(self.router_id):
            entry = self.rip_table.get_entry(neighbor)
            entry.hops = 1
            entry.next_hop = neighbor
            entry.path = [self.router_id, neighbor]
        
        for other_id in self.topology.routers:
            if other_id != self.router_id:
                self.rip_table.get_entry(other_id)
    
    def get_rip_vector(self) -> Dict[str, int]:
        """Get RIP distance vector (hop counts) for sharing."""
        return {dest: entry.hops for dest, entry in self.rip_table.entries.items()}
    
    def receive_rip_vector(self, from_neighbor: str, neighbor_vector: Dict[str, int]) -> List[Tuple[str, int, int]]:
        """
        Process received RIP vector from neighbor.
        Returns list of (destination, old_hops, new_hops) for changed entries.
        """
        changes = []
        
        for dest, neighbor_hops in neighbor_vector.items():
            if dest == self.router_id:
                continue
            
            # RIP: add 1 hop for the link to neighbor
            new_hops = neighbor_hops + 1
            
            # Cap at infinity
            if new_hops > RIP_INFINITY:
                new_hops = RIP_INFINITY
            
            # Only update if neighbor has valid route
            if neighbor_hops >= RIP_INFINITY:
                continue
            
            entry = self.rip_table.get_entry(dest)
            old_hops = entry.hops
            
            if new_hops < old_hops:
                entry.hops = new_hops
                entry.next_hop = from_neighbor
                changes.append((dest, old_hops, new_hops))
            elif new_hops == old_hops and entry.next_hop != from_neighbor:
                # Could implement tie-breaking
                pass
        
        return changes
    
    def rebuild_rip_paths(self, all_routers: Dict[str, 'RIPRouter']) -> None:
        """Rebuild path information from next-hop pointers."""
        for dest, entry in self.rip_table.entries.items():
            if dest == self.router_id:
                entry.path = [self.router_id]
            elif entry.next_hop and entry.is_reachable():
                path = [self.router_id]
                current = entry.next_hop
                visited = {self.router_id}
                
                while current and current != dest and current not in visited:
                    path.append(current)
                    visited.add(current)
                    if current in all_routers:
                        next_entry = all_routers[current].rip_table.get_entry(dest)
                        current = next_entry.next_hop
                    else:
                        break
                
                if current == dest:
                    path.append(dest)
                entry.path = path
            else:
                entry.path = []


class RIPSimulator:
    """RIP protocol simulator with hop-count metric and split horizon support."""
    
    def __init__(self, topology: NetworkTopology, 
                 use_split_horizon: bool = True,
                 use_poisoned_reverse: bool = False,
                 max_iterations: int = 100):
        self.topology = topology
        self.use_split_horizon = use_split_horizon
        self.use_poisoned_reverse = use_poisoned_reverse
        self.max_iterations = max_iterations
        
        self.routers: Dict[str, RIPRouter] = {}
        for router_id in topology.routers:
            self.routers[router_id] = RIPRouter(router_id, topology)
    
    def _get_advertised_vector(self, router_id: str, to_neighbor: str) -> Dict[str, int]:
        """
        Get the vector a router advertises to a specific neighbor.
        Implements split horizon and poisoned reverse if enabled.
        """
        router = self.routers[router_id]
        vector = router.get_rip_vector()
        
        if self.use_split_horizon or self.use_poisoned_reverse:
            advertised = {}
            for dest, hops in vector.items():
                entry = router.rip_table.get_entry(dest)
                # Split horizon: don't advertise routes learned from this neighbor back to them
                if entry.next_hop == to_neighbor:
                    if self.use_poisoned_reverse:
                        advertised[dest] = RIP_INFINITY  # Poisoned reverse
                    else:
                        continue  # Simple split horizon: don't advertise
                else:
                    advertised[dest] = hops
            return advertised
        
        return vector
    
    def run(self, record_history: bool = True) -> DistanceVectorResult:
        """Run RIP simulation."""
        start_time = time.perf_counter()
        iterations: List[DVIterationRecord] = []
        total_messages = 0
        
        # Record initial state
        if record_history:
            initial_tables = {rid: deepcopy(router.rip_table) for rid, router in self.routers.items()}
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
            
            # Synchronous update: collect all vectors first
            vectors_to_send = {}
            for router_id, router in self.routers.items():
                # Each router prepares vectors for each neighbor
                vectors_to_send[router_id] = {}
                neighbors = [n for n, _ in self.topology.get_neighbors(router_id)]
                for neighbor in neighbors:
                    vectors_to_send[router_id][neighbor] = self._get_advertised_vector(router_id, neighbor)
            
            # Process received vectors
            for router_id, router in self.routers.items():
                neighbors = [n for n, _ in self.topology.get_neighbors(router_id)]
                for neighbor in neighbors:
                    neighbor_vector = vectors_to_send[neighbor].get(router_id, {})
                    changes = router.receive_rip_vector(neighbor, neighbor_vector)
                    all_changes.extend([(router_id, dest, old, new) for dest, old, new in changes])
                    iteration_messages += 1
            
            # Rebuild paths
            for router in self.routers.values():
                router.rebuild_rip_paths(self.routers)
            
            total_messages += iteration_messages
            
            converged = len(all_changes) == 0
            
            if record_history:
                current_tables = {rid: deepcopy(router.rip_table) for rid, router in self.routers.items()}
                iterations.append(DVIterationRecord(
                    iteration=iteration,
                    tables=current_tables,
                    messages_sent=iteration_messages,
                    changes=all_changes,
                    converged=converged
                ))
            
            if converged:
                break
        
        final_tables = {rid: router.rip_table for rid, router in self.routers.items()}
        computation_time = time.perf_counter() - start_time
        max_iterations_reached = not converged and iteration >= self.max_iterations
        
        return DistanceVectorResult(
            topology=self.topology,
            strategy=UpdateStrategy.SYNCHRONOUS,
            iterations=iterations,
            final_tables=final_tables,
            converged=converged,
            total_iterations=iteration,
            total_messages=total_messages,
            computation_time=computation_time,
            max_iterations_reached=max_iterations_reached
        )
    
    def get_routing_table(self, router_id: str) -> List[Dict[str, Any]]:
        """Get RIP routing table for a router."""
        if router_id in self.routers:
            return self.routers[router_id].rip_table.to_dict_list()
        return []


def run_rip_simulation(topology: NetworkTopology,
                       use_split_horizon: bool = True,
                       use_poisoned_reverse: bool = False,
                       max_iterations: int = 100,
                       record_history: bool = True) -> DistanceVectorResult:
    """
    Run RIP simulation on the given topology.
    
    Args:
        topology: Network topology
        use_split_horizon: Enable split horizon
        use_poisoned_reverse: Enable poisoned reverse (implies split horizon)
        max_iterations: Maximum iterations
        record_history: Record iteration history
        
    Returns:
        DistanceVectorResult with RIP simulation results
    """
    simulator = RIPSimulator(topology, use_split_horizon, use_poisoned_reverse, max_iterations)
    return simulator.run(record_history=record_history)


def compare_rip_modes(topology: NetworkTopology) -> Dict[str, DistanceVectorResult]:
    """Compare RIP with different loop prevention mechanisms."""
    results = {}
    
    # No loop prevention
    results['none'] = run_rip_simulation(topology, use_split_horizon=False, use_poisoned_reverse=False)
    
    # Split horizon only
    results['split_horizon'] = run_rip_simulation(topology, use_split_horizon=True, use_poisoned_reverse=False)
    
    # Poisoned reverse
    results['poisoned_reverse'] = run_rip_simulation(topology, use_split_horizon=True, use_poisoned_reverse=True)
    
    return results


def demonstrate_rip_vs_cost(topology: NetworkTopology) -> Dict[str, Any]:
    """
    Demonstrate difference between RIP (hop-count) and cost-based routing.
    Returns comparison data.
    """
    # Run RIP
    rip_result = run_rip_simulation(topology)
    
    # Run Link-State (cost-based)
    from algorithms.link_state import run_link_state_for_all_routers
    ls_results = run_link_state_for_all_routers(topology)
    
    comparison = {
        'rip': {},
        'link_state': {},
        'differences': []
    }
    
    for router_id in topology.routers:
        rip_table = rip_result.final_tables[router_id]
        ls_result = ls_results[router_id]
        
        rip_routes = {}
        for entry in rip_table.entries.values():
            if entry.destination != router_id and entry.is_reachable():
                rip_routes[entry.destination] = {
                    'hops': entry.hops,
                    'next_hop': entry.next_hop,
                    'path': entry.path
                }
        
        ls_routes = {}
        for dest in ls_result.distances:
            if dest != router_id and ls_result.distances[dest] != float('inf'):
                ls_routes[dest] = {
                    'cost': ls_result.distances[dest],
                    'next_hop': ls_result.next_hops[dest],
                    'path': ls_result.paths[dest]
                }
        
        comparison['rip'][router_id] = rip_routes
        comparison['link_state'][router_id] = ls_routes
        
        # Find differences
        all_dests = set(rip_routes.keys()) | set(ls_routes.keys())
        for dest in all_dests:
            rip_nh = rip_routes.get(dest, {}).get('next_hop')
            ls_nh = ls_routes.get(dest, {}).get('next_hop')
            if rip_nh != ls_nh:
                comparison['differences'].append({
                    'router': router_id,
                    'destination': dest,
                    'rip_next_hop': rip_nh,
                    'link_state_next_hop': ls_nh,
                    'rip_hops': rip_routes.get(dest, {}).get('hops'),
                    'link_state_cost': ls_routes.get(dest, {}).get('cost')
                })
    
    return comparison