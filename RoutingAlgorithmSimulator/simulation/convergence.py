"""
Convergence Analysis Module

Tracks and analyzes routing algorithm convergence behavior.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from copy import deepcopy
import time
from algorithms.distance_vector import DistanceVectorSimulator, DistanceVectorResult, DVIterationRecord
from algorithms.link_state import LinkStateRouter, LinkStateResult
from algorithms.rip import RIPSimulator
from network.topology import NetworkTopology


@dataclass
class ConvergenceMetrics:
    """Metrics for a single convergence event."""
    algorithm: str
    topology_size: int
    link_count: int
    convergence_time: float
    iterations: int
    messages_exchanged: int
    final_routes_correct: bool
    route_changes: int
    max_distance_change: float


@dataclass
class ConvergenceHistory:
    """Tracks distance evolution over iterations for a specific route."""
    source: str
    destination: str
    distances: List[float]  # Distance at each iteration
    next_hops: List[Optional[str]]  # Next hop at each iteration
    iterations: List[int]


class ConvergenceAnalyzer:
    """Analyzes convergence behavior of routing algorithms."""
    
    def __init__(self, topology: NetworkTopology):
        self.topology = topology
        self.metrics_history: List[ConvergenceMetrics] = []
    
    def analyze_link_state_convergence(self, source: str) -> ConvergenceMetrics:
        """Analyze link-state convergence (essentially single-shot)."""
        router = LinkStateRouter(self.topology)
        
        start = time.perf_counter()
        result = router.compute_shortest_paths(source, record_steps=False)
        convergence_time = time.perf_counter() - start
        
        # Validate against NetworkX
        from algorithms.ospf_validation import OSPFValidator
        validator = OSPFValidator(self.topology)
        validation = validator.validate_single_pair(source, list(self.topology.routers.keys())[0])
        
        return ConvergenceMetrics(
            algorithm="Link-State (Dijkstra)",
            topology_size=len(self.topology.routers),
            link_count=len(self.topology.get_active_links()),
            convergence_time=convergence_time,
            iterations=1,  # Link-state converges in one computation
            messages_exchanged=0,  # Not simulated in basic version
            final_routes_correct=validation.passed,
            route_changes=0,
            max_distance_change=0.0
        )
    
    def analyze_distance_vector_convergence(self, strategy: str = "synchronous") -> ConvergenceMetrics:
        """Analyze distance vector convergence."""
        from algorithms.distance_vector import UpdateStrategy, run_distance_vector
        
        strat = UpdateStrategy.SYNCHRONOUS if strategy == "synchronous" else UpdateStrategy.ASYNCHRONOUS
        
        start = time.perf_counter()
        result = run_distance_vector(self.topology, strat, record_history=True)
        convergence_time = time.perf_counter() - start
        
        # Count total route changes across all iterations
        total_changes = sum(len(rec.changes) for rec in result.iterations)
        
        # Track max distance change
        max_change = 0.0
        for rec in result.iterations:
            for _, old_dist, new_dist in rec.changes:
                if old_dist != float('inf') and new_dist != float('inf'):
                    change = abs(new_dist - old_dist)
                    max_change = max(max_change, change)
        
        # Validate final routes
        from algorithms.ospf_validation import OSPFValidator
        validator = OSPFValidator(self.topology)
        validation_report = validator.validate_all()
        
        return ConvergenceMetrics(
            algorithm=f"Distance-Vector ({strategy})",
            topology_size=len(self.topology.routers),
            link_count=len(self.topology.get_active_links()),
            convergence_time=convergence_time,
            iterations=result.total_iterations,
            messages_exchanged=result.total_messages,
            final_routes_correct=(validation_report.overall_pass_rate == 1.0),
            route_changes=total_changes,
            max_distance_change=max_change
        )
    
    def analyze_rip_convergence(self, use_split_horizon: bool = True) -> ConvergenceMetrics:
        """Analyze RIP convergence."""
        from algorithms.rip import run_rip_simulation
        
        start = time.perf_counter()
        result = run_rip_simulation(self.topology, use_split_horizon=use_split_horizon, record_history=True)
        convergence_time = time.perf_counter() - start
        
        total_changes = sum(len(rec.changes) for rec in result.iterations)
        
        max_change = 0.0
        for rec in result.iterations:
            for _, old_hops, new_hops in rec.changes:
                if old_hops < 16 and new_hops < 16:
                    change = abs(new_hops - old_hops)
                    max_change = max(max_change, change)
        
        # Validate against link-state
        from algorithms.link_state import run_link_state_for_all_routers
        ls_results = run_link_state_for_all_routers(self.topology)
        
        correct = True
        for router_id in self.topology.routers:
            rip_table = result.final_tables[router_id]
            ls_result = ls_results[router_id]
            
            for dest in self.topology.routers:
                if dest == router_id:
                    continue
                rip_entry = rip_table.entries.get(dest)
                ls_dist = ls_result.distances.get(dest, float('inf'))
                
                if rip_entry and rip_entry.is_reachable():
                    # Compare hop count vs cost - they're different metrics
                    # Just check reachability consistency
                    if ls_dist == float('inf'):
                        correct = False
                elif ls_dist != float('inf'):
                    correct = False
        
        return ConvergenceMetrics(
            algorithm=f"RIP (split_horizon={use_split_horizon})",
            topology_size=len(self.topology.routers),
            link_count=len(self.topology.get_active_links()),
            convergence_time=convergence_time,
            iterations=result.total_iterations,
            messages_exchanged=result.total_messages,
            final_routes_correct=correct,
            route_changes=total_changes,
            max_distance_change=max_change
        )
    
    def get_convergence_history(self, dv_result: DistanceVectorResult, 
                                 source: str, destination: str) -> ConvergenceHistory:
        """Extract convergence history for a specific route from DV result."""
        distances = []
        next_hops = []
        iterations = []
        
        for rec in dv_result.iterations:
            table = rec.tables.get(source)
            if table:
                entry = table.get_entry(destination)
                distances.append(entry.distance)
                next_hops.append(entry.next_hop)
                iterations.append(rec.iteration)
        
        return ConvergenceHistory(
            source=source,
            destination=destination,
            distances=distances,
            next_hops=next_hops,
            iterations=iterations
        )
    
    def compare_algorithms(self) -> List[ConvergenceMetrics]:
        """Run and compare all algorithms on current topology."""
        metrics = []
        
        # Link-State (test from first router)
        if self.topology.routers:
            first_router = list(self.topology.routers.keys())[0]
            metrics.append(self.analyze_link_state_convergence(first_router))
        
        # Distance-Vector synchronous
        metrics.append(self.analyze_distance_vector_convergence("synchronous"))
        
        # Distance-Vector asynchronous
        metrics.append(self.analyze_distance_vector_convergence("asynchronous"))
        
        # RIP with split horizon
        metrics.append(self.analyze_rip_convergence(use_split_horizon=True))
        
        # RIP without split horizon
        metrics.append(self.analyze_rip_convergence(use_split_horizon=False))
        
        self.metrics_history.extend(metrics)
        return metrics


def run_convergence_experiment(topology: NetworkTopology) -> Dict[str, Any]:
    """Run a comprehensive convergence experiment."""
    analyzer = ConvergenceAnalyzer(topology)
    metrics = analyzer.compare_algorithms()
    
    return {
        'topology': {
            'routers': len(topology.routers),
            'links': len(topology.get_active_links()),
            'connected': topology.is_connected()
        },
        'metrics': [
            {
                'algorithm': m.algorithm,
                'convergence_time_ms': m.convergence_time * 1000,
                'iterations': m.iterations,
                'messages': m.messages_exchanged,
                'routes_correct': m.final_routes_correct,
                'route_changes': m.route_changes,
                'max_distance_change': m.max_distance_change
            }
            for m in metrics
        ]
    }