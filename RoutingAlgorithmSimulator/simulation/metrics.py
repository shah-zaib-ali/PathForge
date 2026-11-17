"""
Performance Metrics Module

Collects and computes performance metrics for routing algorithm comparison.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from algorithms.link_state import LinkStateRouter, run_link_state_for_all_routers
from algorithms.distance_vector import run_distance_vector, UpdateStrategy
from algorithms.rip import run_rip_simulation
from algorithms.ospf_validation import validate_link_state
from network.topology import NetworkTopology
from simulation.convergence import run_convergence_experiment
import time


@dataclass
class AlgorithmMetrics:
    """Performance metrics for a single algorithm run."""
    algorithm_name: str
    topology_name: str
    num_routers: int
    num_links: int
    
    # Convergence metrics
    convergence_time_ms: float
    iterations_to_converge: int
    messages_exchanged: int
    
    # Route quality metrics
    avg_path_cost: float
    avg_hop_count: float
    routes_correct: bool
    unreachable_destinations: int
    
    # Correctness
    validation_pass_rate: float


@dataclass
class ComparisonResult:
    """Results of comparing multiple algorithms."""
    topology: NetworkTopology
    topology_name: str
    metrics: List[AlgorithmMetrics]
    timestamp: float
    
    def to_dataframe_rows(self) -> List[Dict[str, Any]]:
        """Convert to rows for pandas DataFrame."""
        rows = []
        for m in self.metrics:
            rows.append({
                'Algorithm': m.algorithm_name,
                'Topology': m.topology_name,
                'Routers': m.num_routers,
                'Links': m.num_links,
                'Convergence Time (ms)': round(m.convergence_time_ms, 2),
                'Iterations': m.iterations_to_converge,
                'Messages': m.messages_exchanged,
                'Avg Path Cost': round(m.avg_path_cost, 2) if m.avg_path_cost != float('inf') else '∞',
                'Avg Hops': round(m.avg_hop_count, 2) if m.avg_hop_count != float('inf') else '∞',
                'Routes Correct': '✓' if m.routes_correct else '✗',
                'Unreachable': m.unreachable_destinations,
                'Validation Pass Rate': f"{m.validation_pass_rate:.1%}"
            })
        return rows


class MetricsCollector:
    """Collects and compares metrics across algorithms and topologies."""
    
    def __init__(self):
        self.results: List[ComparisonResult] = []
    
    def measure_link_state(self, topology: NetworkTopology, 
                           topology_name: str) -> AlgorithmMetrics:
        """Measure Link-State algorithm performance."""
        start = time.perf_counter()
        results = run_link_state_for_all_routers(topology)
        convergence_time = (time.perf_counter() - start) * 1000
        
        # Compute average path cost and hop count
        total_cost = 0
        total_hops = 0
        reachable_pairs = 0
        unreachable = 0
        
        for source, result in results.items():
            for dest, dist in result.distances.items():
                if dest == source:
                    continue
                if dist != float('inf'):
                    total_cost += dist
                    total_hops += len(result.paths[dest]) - 1
                    reachable_pairs += 1
                else:
                    unreachable += 1
        
        avg_cost = total_cost / reachable_pairs if reachable_pairs > 0 else float('inf')
        avg_hops = total_hops / reachable_pairs if reachable_pairs > 0 else float('inf')
        
        # Validate
        validation = validate_link_state(topology)
        
        return AlgorithmMetrics(
            algorithm_name="Link-State (Dijkstra)",
            topology_name=topology_name,
            num_routers=len(topology.routers),
            num_links=len(topology.get_active_links()),
            convergence_time_ms=convergence_time,
            iterations_to_converge=1,
            messages_exchanged=0,  # Not simulated in basic LS
            avg_path_cost=avg_cost,
            avg_hop_count=avg_hops,
            routes_correct=(validation.overall_pass_rate == 1.0),
            unreachable_destinations=unreachable,
            validation_pass_rate=validation.overall_pass_rate
        )
    
    def measure_distance_vector(self, topology: NetworkTopology,
                                topology_name: str,
                                strategy: str = "synchronous") -> AlgorithmMetrics:
        """Measure Distance-Vector algorithm performance."""
        strat = UpdateStrategy.SYNCHRONOUS if strategy == "synchronous" else UpdateStrategy.ASYNCHRONOUS
        
        start = time.perf_counter()
        result = run_distance_vector(topology, strat, record_history=True)
        convergence_time = (time.perf_counter() - start) * 1000
        
        # Compute metrics from final tables
        total_cost = 0
        total_hops = 0
        reachable_pairs = 0
        unreachable = 0
        
        for router_id, table in result.final_tables.items():
            for dest, entry in table.entries.items():
                if dest == router_id:
                    continue
                if entry.distance != float('inf'):
                    total_cost += entry.distance
                    total_hops += len(entry.path) - 1 if entry.path else 0
                    reachable_pairs += 1
                else:
                    unreachable += 1
        
        avg_cost = total_cost / reachable_pairs if reachable_pairs > 0 else float('inf')
        avg_hops = total_hops / reachable_pairs if reachable_pairs > 0 else float('inf')
        
        # Validate against link-state
        from algorithms.link_state import run_link_state_for_all_routers
        ls_results = run_link_state_for_all_routers(topology)
        
        correct = True
        for router_id in topology.routers:
            dv_table = result.final_tables[router_id]
            ls_result = ls_results[router_id]
            
            for dest in topology.routers:
                if dest == router_id:
                    continue
                dv_entry = dv_table.get_entry(dest)
                ls_dist = ls_result.distances.get(dest, float('inf'))
                
                if dv_entry.distance != float('inf') and ls_dist == float('inf'):
                    correct = False
                elif dv_entry.distance == float('inf') and ls_dist != float('inf'):
                    correct = False
                elif abs(dv_entry.distance - ls_dist) > 1e-9:
                    correct = False
        
        return AlgorithmMetrics(
            algorithm_name=f"Distance-Vector ({strategy})",
            topology_name=topology_name,
            num_routers=len(topology.routers),
            num_links=len(topology.get_active_links()),
            convergence_time_ms=convergence_time,
            iterations_to_converge=result.total_iterations,
            messages_exchanged=result.total_messages,
            avg_path_cost=avg_cost,
            avg_hop_count=avg_hops,
            routes_correct=correct,
            unreachable_destinations=unreachable,
            validation_pass_rate=1.0 if correct else 0.0
        )
    
    def measure_rip(self, topology: NetworkTopology,
                    topology_name: str,
                    use_split_horizon: bool = True) -> AlgorithmMetrics:
        """Measure RIP algorithm performance."""
        start = time.perf_counter()
        result = run_rip_simulation(topology, use_split_horizon=use_split_horizon, record_history=True)
        convergence_time = (time.perf_counter() - start) * 1000
        
        total_hops = 0
        reachable_pairs = 0
        unreachable = 0
        
        for router_id, table in result.final_tables.items():
            for dest, entry in table.entries.items():
                if dest == router_id:
                    continue
                if entry.is_reachable():
                    total_hops += entry.hops
                    reachable_pairs += 1
                else:
                    unreachable += 1
        
        avg_hops = total_hops / reachable_pairs if reachable_pairs > 0 else float('inf')
        
        # Validate reachability against link-state
        from algorithms.link_state import run_link_state_for_all_routers
        ls_results = run_link_state_for_all_routers(topology)
        
        correct = True
        for router_id in topology.routers:
            rip_table = result.final_tables[router_id]
            ls_result = ls_results[router_id]
            
            for dest in topology.routers:
                if dest == router_id:
                    continue
                rip_entry = rip_table.get_entry(dest)
                ls_dist = ls_result.distances.get(dest, float('inf'))
                
                if rip_entry.is_reachable() and ls_dist == float('inf'):
                    correct = False
                elif not rip_entry.is_reachable() and ls_dist != float('inf'):
                    correct = False
        
        return AlgorithmMetrics(
            algorithm_name=f"RIP (split_horizon={use_split_horizon})",
            topology_name=topology_name,
            num_routers=len(topology.routers),
            num_links=len(topology.get_active_links()),
            convergence_time_ms=convergence_time,
            iterations_to_converge=result.total_iterations,
            messages_exchanged=result.total_messages,
            avg_path_cost=float('inf'),  # RIP uses hops, not cost
            avg_hop_count=avg_hops,
            routes_correct=correct,
            unreachable_destinations=unreachable,
            validation_pass_rate=1.0 if correct else 0.0
        )
    
    def compare_on_topology(self, topology: NetworkTopology, 
                            topology_name: str) -> ComparisonResult:
        """Run all algorithms on a single topology and compare."""
        metrics = []
        
        # Link-State
        metrics.append(self.measure_link_state(topology, topology_name))
        
        # Distance-Vector synchronous
        metrics.append(self.measure_distance_vector(topology, topology_name, "synchronous"))
        
        # Distance-Vector asynchronous
        metrics.append(self.measure_distance_vector(topology, topology_name, "asynchronous"))
        
        # RIP with split horizon
        metrics.append(self.measure_rip(topology, topology_name, use_split_horizon=True))
        
        # RIP without split horizon
        metrics.append(self.measure_rip(topology, topology_name, use_split_horizon=False))
        
        result = ComparisonResult(
            topology=topology,
            topology_name=topology_name,
            metrics=metrics,
            timestamp=time.time()
        )
        
        self.results.append(result)
        return result
    
    def compare_all_scenarios(self) -> List[ComparisonResult]:
        """Run comparison on all predefined scenarios."""
        from network.scenarios import list_scenarios, load_scenario
        
        results = []
        for scenario_key in list_scenarios():
            topo = load_scenario(scenario_key)
            if topo.is_connected() or scenario_key == "disconnected":
                result = self.compare_on_topology(topo, scenario_key)
                results.append(result)
        
        return results
    
    def get_summary_dataframe(self) -> List[Dict[str, Any]]:
        """Get all results as dataframe rows."""
        rows = []
        for result in self.results:
            rows.extend(result.to_dataframe_rows())
        return rows


def run_full_comparison() -> MetricsCollector:
    """Run complete comparison across all scenarios."""
    collector = MetricsCollector()
    collector.compare_all_scenarios()
    return collector


def generate_metrics_summary(collector: MetricsCollector) -> Dict[str, Any]:
    """Generate summary statistics from collected metrics."""
    all_metrics = []
    for result in collector.results:
        all_metrics.extend(result.metrics)
    
    # Group by algorithm
    by_algorithm = {}
    for m in all_metrics:
        if m.algorithm_name not in by_algorithm:
            by_algorithm[m.algorithm_name] = []
        by_algorithm[m.algorithm_name].append(m)
    
    summary = {}
    for alg_name, metrics_list in by_algorithm.items():
        summary[alg_name] = {
            'avg_convergence_time_ms': sum(m.convergence_time_ms for m in metrics_list) / len(metrics_list),
            'avg_iterations': sum(m.iterations_to_converge for m in metrics_list) / len(metrics_list),
            'avg_messages': sum(m.messages_exchanged for m in metrics_list) / len(metrics_list),
            'correctness_rate': sum(1 for m in metrics_list if m.routes_correct) / len(metrics_list),
            'run_count': len(metrics_list)
        }
    
    return summary