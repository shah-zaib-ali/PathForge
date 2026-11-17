"""
Tests for Distance-Vector Routing Algorithm
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.distance_vector import (
    DistanceVectorRouter, DistanceVectorSimulator, DistanceVectorResult,
    DistanceVectorTable, DVIterationRecord, UpdateStrategy,
    run_distance_vector, compare_strategies
)
from network.topology import NetworkTopology, create_predefined_scenario


class TestDistanceVectorRouting(unittest.TestCase):
    """Test cases for Distance-Vector routing implementation."""

    def setUp(self):
        """Set up test topologies."""
        self.simple_topo = create_predefined_scenario("simple_three")
        self.multi_path_topo = create_predefined_scenario("multiple_paths")
        self.dv_loop_topo = create_predefined_scenario("distance_vector_loop")
        self.disconnected_topo = create_predefined_scenario("disconnected")
        self.link_failure_topo = create_predefined_scenario("link_failure")

    def test_dv_convergence_simple_three(self):
        """Test DV convergence on simple 3-router network."""
        result = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertTrue(result.converged)
        self.assertLessEqual(result.total_iterations, 5)
        
        # Check final distances from R1
        r1_table = result.final_tables["R1"]
        self.assertEqual(r1_table.get_entry("R1").distance, 0.0)
        self.assertEqual(r1_table.get_entry("R2").distance, 1.0)
        self.assertEqual(r1_table.get_entry("R3").distance, 2.0)  # Via R2

    def test_dv_multiple_paths(self):
        """Test DV with multiple alternative paths."""
        result = run_distance_vector(self.multi_path_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertTrue(result.converged)
        
        # Check R1 to R5 converges to cost 6
        r1_table = result.final_tables["R1"]
        self.assertEqual(r1_table.get_entry("R5").distance, 6.0)

    def test_dv_synchronous_vs_asynchronous(self):
        """Test both update strategies produce same final routes."""
        sync_result = run_distance_vector(self.multi_path_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        async_result = run_distance_vector(self.multi_path_topo, UpdateStrategy.ASYNCHRONOUS, record_history=True)
        
        # Both should converge
        self.assertTrue(sync_result.converged)
        self.assertTrue(async_result.converged)
        
        # Final routes should match
        for router_id in self.multi_path_topo.routers:
            sync_table = sync_result.final_tables[router_id]
            async_table = async_result.final_tables[router_id]
            
            for dest in sync_table.entries:
                sync_entry = sync_table.get_entry(dest)
                async_entry = async_table.get_entry(dest)
                self.assertEqual(sync_entry.distance, async_entry.distance)
                self.assertEqual(sync_entry.next_hop, async_entry.next_hop)

    def test_dv_disconnected_destination(self):
        """Test DV with disconnected components."""
        result = run_distance_vector(self.disconnected_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertTrue(result.converged)
        
        # R1 cannot reach R3, R4
        r1_table = result.final_tables["R1"]
        self.assertEqual(r1_table.get_entry("R3").distance, float('inf'))
        self.assertEqual(r1_table.get_entry("R4").distance, float('inf'))
        self.assertIsNone(r1_table.get_entry("R3").next_hop)

    def test_dv_link_cost_change(self):
        """Test DV adapts to link cost changes."""
        # Initial run
        result1 = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        r1_table1 = result1.final_tables["R1"]
        self.assertEqual(r1_table1.get_entry("R3").distance, 2.0)
        
        # Change link cost
        self.simple_topo.update_link_cost("R1", "R3", 1.0)
        
        # Re-run
        result2 = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        r1_table2 = result2.final_tables["R1"]
        self.assertEqual(r1_table2.get_entry("R3").distance, 1.0)
        self.assertEqual(r1_table2.get_entry("R3").next_hop, "R3")

    def test_dv_link_failure_recovery(self):
        """Test DV recovers from link failure."""
        # Use link_failure scenario: R1-R2-R3-R4 with R1-R4 backup
        result1 = run_distance_vector(self.link_failure_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        # Initial: R1 to R4 via R2-R3 (cost 3) or direct (cost 10)
        r1_table1 = result1.final_tables["R1"]
        self.assertEqual(r1_table1.get_entry("R4").distance, 3.0)
        self.assertEqual(r1_table1.get_entry("R4").next_hop, "R2")
        
        # Fail R2-R3 link
        self.link_failure_topo.set_link_failed("R2", "R3", True)
        
        result2 = run_distance_vector(self.link_failure_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        r1_table2 = result2.final_tables["R1"]
        # Now must use direct R1-R4 (cost 10)
        self.assertEqual(r1_table2.get_entry("R4").distance, 10.0)
        self.assertEqual(r1_table2.get_entry("R4").next_hop, "R4")

    def test_dv_iteration_recording(self):
        """Test iteration history recording."""
        result = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertIsInstance(result.iterations, list)
        self.assertGreater(len(result.iterations), 1)
        
        # Check iteration 0 (initial)
        iter0 = result.iterations[0]
        self.assertEqual(iter0.iteration, 0)
        self.assertEqual(iter0.messages_sent, 0)
        
        # Check final iteration
        final_iter = result.iterations[-1]
        self.assertEqual(final_iter.iteration, result.total_iterations)
        self.assertTrue(final_iter.converged)

    def test_dv_changes_tracking(self):
        """Test that route changes are tracked per iteration."""
        result = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        # Should have changes in early iterations
        total_changes = sum(len(rec.changes) for rec in result.iterations)
        self.assertGreater(total_changes, 0)
        
        # Final iteration should have no changes
        final_iter = result.iterations[-1]
        self.assertEqual(len(final_iter.changes), 0)

    def test_dv_max_iterations_limit(self):
        """Test max iterations limit prevents infinite loop."""
        # Create topology that might not converge quickly
        topo = NetworkTopology()
        for i in range(6):
            topo.add_router(f"R{i+1}")
        topo.add_link("R1", "R2", 1)
        topo.add_link("R2", "R3", 1)
        topo.add_link("R3", "R4", 1)
        topo.add_link("R4", "R5", 1)
        topo.add_link("R5", "R6", 1)
        
        result = run_distance_vector(topo, UpdateStrategy.SYNCHRONOUS, max_iterations=3, record_history=True)
        
        # Should stop at max iterations
        self.assertTrue(result.max_iterations_reached)
        self.assertEqual(result.total_iterations, 3)

    def test_dv_routing_table_format(self):
        """Test routing table output format."""
        result = run_distance_vector(self.simple_topo, UpdateStrategy.SYNCHRONOUS, record_history=False)
        
        table = result.final_tables["R1"].to_dict_list()
        
        self.assertIsInstance(table, list)
        self.assertEqual(len(table), 2)  # R2 and R3
        
        for entry in table:
            self.assertIn('Destination', entry)
            self.assertIn('Next Hop', entry)
            self.assertIn('Distance', entry)
            self.assertIn('Path', entry)

    def test_dv_compare_strategies_function(self):
        """Test compare_strategies convenience function."""
        results = compare_strategies(self.simple_topo)
        
        self.assertIn('synchronous', results)
        self.assertIn('asynchronous', results)
        self.assertIsInstance(results['synchronous'], DistanceVectorResult)
        self.assertIsInstance(results['asynchronous'], DistanceVectorResult)


class TestDistanceVectorEdgeCases(unittest.TestCase):
    """Test edge cases for Distance-Vector."""

    def setUp(self):
        """Set up test topologies."""
        self.simple_topo = create_predefined_scenario("simple_three")

    def test_single_router_topology(self):
        """Test DV with single router."""
        topo = NetworkTopology()
        topo.add_router("R1")
        
        result = run_distance_vector(topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertTrue(result.converged)
        self.assertEqual(result.total_iterations, 1)
        
        table = result.final_tables["R1"]
        self.assertEqual(table.get_entry("R1").distance, 0.0)

    def test_two_router_topology(self):
        """Test DV with two routers."""
        topo = NetworkTopology()
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        topo.add_link(r1.id, r2.id, 5.0)
        
        result = run_distance_vector(topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        
        self.assertTrue(result.converged)
        r1_table = result.final_tables["R1"]
        self.assertEqual(r1_table.get_entry("R2").distance, 5.0)
        self.assertEqual(r1_table.get_entry("R2").next_hop, "R2")

    def test_router_initialization(self):
        """Test router initializes with direct neighbors."""
        router = DistanceVectorRouter("R1", self.simple_topo)
        
        # Should know direct neighbors
        self.assertEqual(router.table.get_entry("R2").distance, 1.0)
        self.assertEqual(router.table.get_entry("R2").next_hop, "R2")
        self.assertEqual(router.table.get_entry("R3").distance, 3.0)  # Direct link
        self.assertEqual(router.table.get_entry("R3").next_hop, "R3")
        
        # Self distance
        self.assertEqual(router.table.get_entry("R1").distance, 0.0)
        self.assertEqual(router.table.get_entry("R1").next_hop, "R1")

    def test_receive_vector_updates(self):
        """Test receiving and processing neighbor vector."""
        router = DistanceVectorRouter("R1", self.simple_topo)
        
        # Simulate receiving from R2
        neighbor_vector = {"R1": 1.0, "R2": 0.0, "R3": 1.0}
        changes = router.receive_vector("R2", neighbor_vector)
        
        # R1 learns R3 via R2 at cost 2 (better than direct 3)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0][0], "R3")
        self.assertEqual(changes[0][2], 2.0)  # new distance
        
        # Next hop should be updated
        self.assertEqual(router.table.get_entry("R3").next_hop, "R2")


if __name__ == '__main__':
    unittest.main()