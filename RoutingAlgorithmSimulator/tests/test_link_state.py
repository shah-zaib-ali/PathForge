"""
Tests for Link-State Routing Algorithm
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.link_state import (
    LinkStateRouter, LinkStateResult, DijkstraStep,
    run_link_state_for_all_routers, simulate_lsa_flooding
)
from network.topology import NetworkTopology, create_predefined_scenario


class TestLinkStateRouting(unittest.TestCase):
    """Test cases for Link-State routing implementation."""

    def setUp(self):
        """Set up test topologies."""
        self.simple_topo = create_predefined_scenario("simple_three")
        self.multi_path_topo = create_predefined_scenario("multiple_paths")
        self.cost_vs_hops_topo = create_predefined_scenario("cost_vs_hops")
        self.disconnected_topo = create_predefined_scenario("disconnected")

    def test_dijkstra_simple_three_router(self):
        """Test Dijkstra on simple 3-router triangle."""
        router = LinkStateRouter(self.simple_topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        
        # R1 to R2: direct cost 1
        self.assertEqual(result.distances["R2"], 1.0)
        self.assertEqual(result.next_hops["R2"], "R2")
        
        # R1 to R3: direct cost 3, but via R2 is 2
        self.assertEqual(result.distances["R3"], 2.0)
        self.assertEqual(result.next_hops["R3"], "R2")
        self.assertEqual(result.paths["R3"], ["R1", "R2", "R3"])

    def test_dijkstra_multiple_paths(self):
        """Test Dijkstra with multiple alternative paths."""
        router = LinkStateRouter(self.multi_path_topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        
        # R1 to R5: multiple paths exist
        # R1-R2-R4-R5: 2+2+2=6
        # R1-R3-R4-R5: 3+1+2=6
        # R1-R2-R5: 2+4=6
        # R1-R3-R5: 3+3=6
        # All cost 6, should pick one
        self.assertEqual(result.distances["R5"], 6.0)
        self.assertIn(result.next_hops["R5"], ["R2", "R3"])

    def test_dijkstra_cost_vs_hops(self):
        """Test that lowest cost path chosen over fewest hops."""
        router = LinkStateRouter(self.cost_vs_hops_topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        
        # R1 to R4: 
        # Direct via R2: 2 hops, cost 10 (5+5)
        # Via R3: 3 hops, cost 6 (2+2+2) - wait, let me check the topology
        # Actually: R1-R2(5), R2-R4(5) = cost 10, 2 hops
        # R1-R3(2), R3-R2(2), R2-R4(2) = cost 6, 3 hops
        # Lowest cost is 6 via R3
        self.assertEqual(result.distances["R4"], 6.0)
        self.assertEqual(result.next_hops["R4"], "R3")

    def test_dijkstra_disconnected_destination(self):
        """Test handling of unreachable destinations."""
        router = LinkStateRouter(self.disconnected_topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        
        # R3 and R4 are in separate component
        self.assertEqual(result.distances["R3"], float('inf'))
        self.assertEqual(result.distances["R4"], float('inf'))
        self.assertIsNone(result.next_hops["R3"])
        self.assertIsNone(result.next_hops["R4"])
        self.assertEqual(result.paths["R3"], [])
        self.assertEqual(result.paths["R4"], [])

    def test_dijkstra_link_cost_change(self):
        """Test recomputation after link cost change."""
        router = LinkStateRouter(self.simple_topo)
        
        # Initial: R1-R3 direct cost 3
        result1 = router.compute_shortest_paths("R1", record_steps=False)
        self.assertEqual(result1.distances["R3"], 2.0)  # Via R2
        
        # Change R1-R3 to cost 1
        self.simple_topo.update_link_cost("R1", "R3", 1.0)
        router.update_topology(self.simple_topo)
        
        result2 = router.compute_shortest_paths("R1", record_steps=False)
        self.assertEqual(result2.distances["R3"], 1.0)  # Now direct
        self.assertEqual(result2.next_hops["R3"], "R3")

    def test_dijkstra_link_failure(self):
        """Test recomputation after link failure."""
        router = LinkStateRouter(self.simple_topo)
        
        # Initial: R1-R2-R3 path exists
        result1 = router.compute_shortest_paths("R1", record_steps=False)
        self.assertEqual(result1.distances["R3"], 2.0)
        
        # Fail R2-R3 link
        self.simple_topo.set_link_failed("R2", "R3", True)
        router.update_topology(self.simple_topo)
        
        result2 = router.compute_shortest_paths("R1", record_steps=False)
        # Now only direct R1-R3 (cost 3) available
        self.assertEqual(result2.distances["R3"], 3.0)
        self.assertEqual(result2.next_hops["R3"], "R3")
        
        # Restore link
        self.simple_topo.set_link_failed("R2", "R3", False)
        router.update_topology(self.simple_topo)
        
        result3 = router.compute_shortest_paths("R1", record_steps=False)
        self.assertEqual(result3.distances["R3"], 2.0)

    def test_dijkstra_step_recording(self):
        """Test step-by-step recording for educational display."""
        router = LinkStateRouter(self.simple_topo)
        result = router.compute_shortest_paths("R1", record_steps=True)
        
        self.assertIsInstance(result.steps, list)
        self.assertGreater(len(result.steps), 0)
        
        # First step should be initialization
        self.assertEqual(result.steps[0].iteration, 0)
        self.assertIsNone(result.steps[0].current_node)
        
        # Last step should be completion
        last_step = result.steps[-1]
        self.assertIn("complete", last_step.description.lower())

    def test_dijkstra_single_router(self):
        """Test with single router topology."""
        topo = NetworkTopology()
        topo.add_router("R1")
        
        router = LinkStateRouter(topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        
        self.assertEqual(result.distances["R1"], 0.0)
        self.assertEqual(result.next_hops["R1"], "R1")
        self.assertEqual(result.paths["R1"], ["R1"])

    def test_dijkstra_empty_topology(self):
        """Test with empty topology."""
        topo = NetworkTopology()
        router = LinkStateRouter(topo)
        
        # Should handle gracefully - source not in topology still gets distance 0
        result = router.compute_shortest_paths("R1", record_steps=False)
        self.assertEqual(result.distances, {"R1": 0.0})
        # Paths and next_hops are empty because R1 doesn't exist in topology
        self.assertEqual(result.paths, {})
        self.assertEqual(result.next_hops, {})

    def test_run_all_routers(self):
        """Test running link-state for all routers."""
        results = run_link_state_for_all_routers(self.simple_topo, record_steps=False)
        
        self.assertEqual(len(results), 3)
        for router_id in ["R1", "R2", "R3"]:
            self.assertIn(router_id, results)
            self.assertIsInstance(results[router_id], LinkStateResult)

    def test_lsa_flooding_simulation(self):
        """Test LSA flooding simulation."""
        lsa_db = simulate_lsa_flooding(self.simple_topo)
        
        # All routers should have same topology database
        for router_id in ["R1", "R2", "R3"]:
            self.assertIn(router_id, lsa_db)
            # Each should know about all links
            db = lsa_db[router_id]
            self.assertIn("R1", db)
            self.assertIn("R2", db)
            self.assertIn("R3", db)

    def test_routing_table_format(self):
        """Test routing table output format."""
        router = LinkStateRouter(self.simple_topo)
        result = router.compute_shortest_paths("R1", record_steps=False)
        table = result.get_routing_table()
        
        self.assertIsInstance(table, list)
        self.assertEqual(len(table), 2)  # R2 and R3
        
        for entry in table:
            self.assertIn('Destination', entry)
            self.assertIn('Next Hop', entry)
            self.assertIn('Cost', entry)
            self.assertIn('Path', entry)


class TestLinkStateEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_negative_link_cost_rejected(self):
        """Test that negative link costs are rejected at topology level."""
        topo = NetworkTopology()
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        
        with self.assertRaises(ValueError):
            topo.add_link(r1.id, r2.id, -1.0)
        
        with self.assertRaises(ValueError):
            topo.add_link(r1.id, r2.id, 0.0)

    def test_duplicate_router_rejected(self):
        """Test that duplicate router names are rejected."""
        topo = NetworkTopology()
        topo.add_router("R1")
        
        with self.assertRaises(ValueError):
            topo.add_router("R1")

    def test_self_loop_rejected(self):
        """Test that self-loops are rejected."""
        topo = NetworkTopology()
        r1 = topo.add_router("R1")
        
        with self.assertRaises(ValueError):
            topo.add_link(r1.id, r1.id, 1.0)


if __name__ == '__main__':
    unittest.main()