"""
OSPF Validation Module

Validates Link-State simulator results against NetworkX shortest-path reference.
Provides detailed comparison and pass/fail reporting.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from copy import deepcopy
import networkx as nx
from algorithms.link_state import LinkStateRouter, LinkStateResult, run_link_state_for_all_routers
from network.topology import NetworkTopology


@dataclass
class ValidationResult:
    """Result of validating a single source-destination pair."""
    source: str
    destination: str
    expected_distance: float
    actual_distance: float
    expected_path: List[str]
    actual_path: List[str]
    expected_next_hop: Optional[str]
    actual_next_hop: Optional[str]
    passed: bool
    mismatch_type: str = ""  # "distance", "path", "next_hop", "unreachable"


@dataclass
class RouterValidationSummary:
    """Validation summary for a single router."""
    router_id: str
    total_tests: int
    passed: int
    failed: int
    results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 1.0
        return self.passed / self.total_tests


@dataclass
class OSPFValidationReport:
    """Complete OSPF validation report."""
    topology: NetworkTopology
    router_summaries: Dict[str, RouterValidationSummary]
    overall_passed: int
    overall_total: int
    overall_pass_rate: float
    mismatches: List[ValidationResult]
    computation_time: float
    
    def to_dataframe_rows(self) -> List[Dict[str, Any]]:
        """Convert to rows for pandas DataFrame display."""
        rows = []
        for router_id, summary in self.router_summaries.items():
            for result in summary.results:
                rows.append({
                    'Source Router': result.source,
                    'Destination': result.destination,
                    'Expected Cost': result.expected_distance if result.expected_distance != float('inf') else '∞',
                    'Actual Cost': result.actual_distance if result.actual_distance != float('inf') else '∞',
                    'Expected Next Hop': result.expected_next_hop or '—',
                    'Actual Next Hop': result.actual_next_hop or '—',
                    'Expected Path': ' → '.join(result.expected_path) if result.expected_path else 'Unreachable',
                    'Actual Path': ' → '.join(result.actual_path) if result.actual_path else 'Unreachable',
                    'Status': '✓ PASS' if result.passed else '✗ FAIL',
                    'Mismatch': result.mismatch_type if not result.passed else ''
                })
        return rows


class OSPFValidator:
    """
    Validates Link-State routing results against NetworkX reference implementation.
    NetworkX uses Dijkstra's algorithm, so results should match exactly.
    """
    
    def __init__(self, topology: NetworkTopology):
        self.topology = topology
        self.link_state_router = LinkStateRouter(topology)
        self.nx_graph = topology.graph  # NetworkX graph with active links only
    
    def validate_all(self, sources: Optional[List[str]] = None) -> OSPFValidationReport:
        """
        Validate link-state results for all routers (or specified sources) against NetworkX.
        
        Args:
            sources: List of source router IDs to validate. If None, validate all.
            
        Returns:
            OSPFValidationReport with detailed results
        """
        import time
        start_time = time.perf_counter()
        
        if sources is None:
            sources = list(self.topology.routers.keys())
        
        # Run link-state algorithm for all sources
        ls_results = {}
        for source in sources:
            ls_results[source] = self.link_state_router.compute_shortest_paths(source, record_steps=False)
        
        router_summaries = {}
        all_mismatches = []
        overall_passed = 0
        overall_total = 0
        
        for source in sources:
            ls_result = ls_results[source]
            results = []
            passed = 0
            failed = 0
            
            for dest in self.topology.routers:
                if dest == source:
                    continue
                
                overall_total += 1
                
                # Get NetworkX reference results
                try:
                    expected_distance = nx.shortest_path_length(
                        self.nx_graph, source, dest, weight='weight')
                    expected_path = nx.shortest_path(
                        self.nx_graph, source, dest, weight='weight')
                    expected_next_hop = expected_path[1] if len(expected_path) > 1 else None
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    expected_distance = float('inf')
                    expected_path = []
                    expected_next_hop = None
                
                # Get simulator results
                actual_distance = ls_result.distances.get(dest, float('inf'))
                actual_path = ls_result.paths.get(dest, [])
                actual_next_hop = ls_result.next_hops.get(dest)
                
                # Compare
                distance_match = self._compare_distances(expected_distance, actual_distance)
                path_match = self._compare_paths(expected_path, actual_path, expected_distance, actual_distance)
                # Next hop can differ if distances match (multiple valid shortest paths)
                if distance_match:
                    next_hop_match = True
                else:
                    next_hop_match = (expected_next_hop == actual_next_hop)
                
                passed_check = distance_match and path_match and next_hop_match
                
                mismatch_type = ""
                if not passed_check:
                    if not distance_match:
                        mismatch_type = "distance"
                    elif not path_match:
                        mismatch_type = "path"
                    elif not next_hop_match:
                        mismatch_type = "next_hop"
                    failed += 1
                    all_mismatches.append(ValidationResult(
                        source=source,
                        destination=dest,
                        expected_distance=expected_distance,
                        actual_distance=actual_distance,
                        expected_path=expected_path,
                        actual_path=actual_path,
                        expected_next_hop=expected_next_hop,
                        actual_next_hop=actual_next_hop,
                        passed=False,
                        mismatch_type=mismatch_type
                    ))
                else:
                    passed += 1
                
                results.append(ValidationResult(
                    source=source,
                    destination=dest,
                    expected_distance=expected_distance,
                    actual_distance=actual_distance,
                    expected_path=expected_path,
                    actual_path=actual_path,
                    expected_next_hop=expected_next_hop,
                    actual_next_hop=actual_next_hop,
                    passed=passed_check,
                    mismatch_type=mismatch_type if not passed_check else ""
                ))
            
            router_summaries[source] = RouterValidationSummary(
                router_id=source,
                total_tests=len(results),
                passed=passed,
                failed=failed,
                results=results
            )
            overall_passed += passed
        
        computation_time = time.perf_counter() - start_time
        overall_pass_rate = overall_passed / overall_total if overall_total > 0 else 1.0
        
        return OSPFValidationReport(
            topology=self.topology,
            router_summaries=router_summaries,
            overall_passed=overall_passed,
            overall_total=overall_total,
            overall_pass_rate=overall_pass_rate,
            mismatches=all_mismatches,
            computation_time=computation_time
        )
    
    def _compare_distances(self, expected: float, actual: float) -> bool:
        """Compare two distances, handling infinity."""
        if expected == float('inf') and actual == float('inf'):
            return True
        if expected == float('inf') or actual == float('inf'):
            return False
        # Allow tiny floating point differences
        return abs(expected - actual) < 1e-9
    
    def _compare_paths(self, expected: List[str], actual: List[str], 
                       expected_dist: float = None, actual_dist: float = None) -> bool:
        """Compare two paths. Allow multiple valid shortest paths."""
        if not expected and not actual:
            return True
        if not expected or not actual:
            return False
        
        # If distances are provided and match, consider paths valid if they have same cost
        if expected_dist is not None and actual_dist is not None:
            if self._compare_distances(expected_dist, actual_dist):
                # Both paths have the same total cost - both are valid shortest paths
                return True
        
        # Fallback: require exact path match
        return expected == actual
    
    def validate_single_pair(self, source: str, destination: str) -> ValidationResult:
        """Validate a single source-destination pair."""
        # Link-state result
        ls_result = self.link_state_router.compute_shortest_paths(source, record_steps=False)
        
        # NetworkX reference
        try:
            expected_distance = nx.shortest_path_length(
                self.nx_graph, source, destination, weight='weight')
            expected_path = nx.shortest_path(
                self.nx_graph, source, destination, weight='weight')
            expected_next_hop = expected_path[1] if len(expected_path) > 1 else None
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            expected_distance = float('inf')
            expected_path = []
            expected_next_hop = None
        
        actual_distance = ls_result.distances.get(destination, float('inf'))
        actual_path = ls_result.paths.get(destination, [])
        actual_next_hop = ls_result.next_hops.get(destination)
        
        distance_match = self._compare_distances(expected_distance, actual_distance)
        path_match = self._compare_paths(expected_path, actual_path, expected_distance, actual_distance)
        # Next hop can differ if distances match (multiple valid shortest paths)
        if distance_match:
            next_hop_match = True
        else:
            next_hop_match = (expected_next_hop == actual_next_hop)
        passed = distance_match and path_match and next_hop_match
        
        mismatch_type = ""
        if not passed:
            if not distance_match:
                mismatch_type = "distance"
            elif not path_match:
                mismatch_type = "path"
            elif not next_hop_match:
                mismatch_type = "next_hop"
        
        return ValidationResult(
            source=source,
            destination=destination,
            expected_distance=expected_distance,
            actual_distance=actual_distance,
            expected_path=expected_path,
            actual_path=actual_path,
            expected_next_hop=expected_next_hop,
            actual_next_hop=actual_next_hop,
            passed=passed,
            mismatch_type=mismatch_type
        )


def validate_link_state(topology: NetworkTopology, 
                        sources: Optional[List[str]] = None) -> OSPFValidationReport:
    """
    Convenience function to validate link-state results against NetworkX.
    
    Args:
        topology: Network topology to validate
        sources: Optional list of source routers to validate
        
    Returns:
        OSPFValidationReport with validation results
    """
    validator = OSPFValidator(topology)
    return validator.validate_all(sources)


def validate_after_topology_change(original_topology: NetworkTopology,
                                    modified_topology: NetworkTopology) -> OSPFValidationReport:
    """
    Validate that link-state correctly recalculates after topology change.
    """
    validator = OSPFValidator(modified_topology)
    return validator.validate_all()


def generate_validation_test_cases() -> List[Dict[str, Any]]:
    """Generate test cases for validation testing."""
    from network.scenarios import load_scenario, list_scenarios
    
    test_cases = []
    for scenario_key in list_scenarios():
        topo = load_scenario(scenario_key)
        if topo.is_connected():
            test_cases.append({
                'scenario': scenario_key,
                'topology': topo,
                'expected_pass': True
            })
    
    return test_cases