"""
Tests for Network Topology Management
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from network.topology import (
    NetworkTopology, Router, Link, create_predefined_scenario, create_random_topology
)
from network.scenarios import load_scenario, list_scenarios, SCENARIOS


class TestNetworkTopology(unittest.TestCase):
    """Test cases for NetworkTopology class."""

    def setUp(self):
        """Set up basic topology for tests."""
        self.topo = NetworkTopology()

    def test_add_router(self):
        """Test adding routers."""
        router = self.topo.add_router("R1")
        
        self.assertIsInstance(router, Router)
        self.assertEqual(router.name, "R1")
        self.assertEqual(router.id, "R1")  # First router gets R1
        self.assertIn("R1", self.topo.routers)
        self.assertEqual(len(self.topo.routers), 1)

    def test_add_multiple_routers(self):
        """Test adding multiple routers gets sequential IDs."""
        r1 = self.topo.add_router("RouterA")
        r2 = self.topo.add_router("RouterB")
        r3 = self.topo.add_router("RouterC")
        
        self.assertEqual(r1.id, "R1")
        self.assertEqual(r2.id, "R2")
        self.assertEqual(r3.id, "R3")
        self.assertEqual(len(self.topo.routers), 3)

    def test_duplicate_router_rejected(self):
        """Test duplicate router name raises error."""
        self.topo.add_router("R1")
        
        with self.assertRaises(ValueError):
            self.topo.add_router("R1")

    def test_remove_router(self):
        """Test removing router."""
        self.topo.add_router("R1")
        self.topo.add_router("R2")
        
        result = self.topo.remove_router("R1")
        
        self.assertTrue(result)
        self.assertNotIn("R1", self.topo.routers)
        self.assertEqual(len(self.topo.routers), 1)

    def test_remove_nonexistent_router(self):
        """Test removing non-existent router returns False."""
        result = self.topo.remove_router("R999")
        self.assertFalse(result)

    def test_remove_router_removes_links(self):
        """Test removing router also removes its links."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        r3 = self.topo.add_router("R3")
        self.topo.add_link(r1.id, r2.id, 1.0)
        self.topo.add_link(r1.id, r3.id, 2.0)
        
        self.topo.remove_router("R1")
        
        self.assertEqual(len(self.topo.links), 0)

    def test_add_link(self):
        """Test adding links between routers."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        
        link = self.topo.add_link(r1.id, r2.id, 5.0)
        
        self.assertIsInstance(link, Link)
        self.assertEqual(link.source, r1.id)
        self.assertEqual(link.target, r2.id)
        self.assertEqual(link.cost, 5.0)
        self.assertFalse(link.is_failed)
        self.assertEqual(len(self.topo.links), 1)

    def test_add_link_undirected(self):
        """Test links are undirected (same regardless of order)."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        
        link1 = self.topo.add_link(r1.id, r2.id, 1.0)
        
        # Adding reverse should fail (duplicate)
        with self.assertRaises(ValueError):
            self.topo.add_link(r2.id, r1.id, 2.0)
        
        self.assertEqual(len(self.topo.links), 1)

    def test_self_loop_rejected(self):
        """Test self-loops are rejected."""
        r1 = self.topo.add_router("R1")
        
        with self.assertRaises(ValueError):
            self.topo.add_link(r1.id, r1.id, 1.0)

    def test_negative_cost_rejected(self):
        """Test negative/zero costs are rejected."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        
        with self.assertRaises(ValueError):
            self.topo.add_link(r1.id, r2.id, -1.0)
        
        with self.assertRaises(ValueError):
            self.topo.add_link(r1.id, r2.id, 0.0)

    def test_nonexistent_router_rejected(self):
        """Test adding link with non-existent router fails."""
        r1 = self.topo.add_router("R1")
        
        with self.assertRaises(ValueError):
            self.topo.add_link(r1.id, "R999", 1.0)

    def test_remove_link(self):
        """Test removing link by ID."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        link = self.topo.add_link(r1.id, r2.id, 1.0)
        
        result = self.topo.remove_link(link.id)
        
        self.assertTrue(result)
        self.assertEqual(len(self.topo.links), 0)

    def test_update_link_cost(self):
        """Test updating link cost."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        
        result = self.topo.update_link_cost(r1.id, r2.id, 10.0)
        
        self.assertTrue(result)
        link = self.topo.links["R1-R2"]
        self.assertEqual(link.cost, 10.0)

    def test_set_link_failed(self):
        """Test marking link as failed."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        
        # Fail the link
        result = self.topo.set_link_failed(r1.id, r2.id, True)
        
        self.assertTrue(result)
        link = self.topo.links["R1-R2"]
        self.assertTrue(link.is_failed)
        
        # Should not appear in active links
        active = self.topo.get_active_links()
        self.assertEqual(len(active), 0)
        
        # Restore the link
        result = self.topo.set_link_failed(r1.id, r2.id, False)
        self.assertFalse(link.is_failed)
        self.assertEqual(len(self.topo.get_active_links()), 1)

    def test_get_neighbors(self):
        """Test getting neighbor information."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        r3 = self.topo.add_router("R3")
        self.topo.add_link(r1.id, r2.id, 2.0)
        self.topo.add_link(r1.id, r3.id, 3.0)
        
        neighbors = self.topo.get_neighbors(r1.id)
        
        self.assertEqual(len(neighbors), 2)
        self.assertIn((r2.id, 2.0), neighbors)
        self.assertIn((r3.id, 3.0), neighbors)

    def test_get_neighbors_excludes_failed(self):
        """Test failed links excluded from neighbors."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        self.topo.set_link_failed(r1.id, r2.id, True)
        
        neighbors = self.topo.get_neighbors(r1.id)
        self.assertEqual(len(neighbors), 0)

    def test_is_connected(self):
        """Test connectivity check."""
        # Empty topology
        self.assertTrue(self.topo.is_connected())
        
        # Single router
        self.topo.add_router("R1")
        self.assertTrue(self.topo.is_connected())
        
        # Two connected routers
        r2 = self.topo.add_router("R2")
        self.topo.add_link("R1", "R2", 1.0)
        self.assertTrue(self.topo.is_connected())
        
        # Disconnected
        r3 = self.topo.add_router("R3")
        self.assertFalse(self.topo.is_connected())

    def test_shortest_path_networkx(self):
        """Test NetworkX shortest path integration."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        r3 = self.topo.add_router("R3")
        self.topo.add_link(r1.id, r2.id, 1.0)
        self.topo.add_link(r2.id, r3.id, 1.0)
        self.topo.add_link(r1.id, r3.id, 5.0)
        
        path = self.topo.get_shortest_path("R1", "R3")
        self.assertEqual(path, ["R1", "R2", "R3"])
        
        length = self.topo.get_shortest_path_length("R1", "R3")
        self.assertEqual(length, 2.0)

    def test_shortest_path_unreachable(self):
        """Test shortest path for unreachable destination."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        # No link between them
        
        path = self.topo.get_shortest_path("R1", "R2")
        self.assertIsNone(path)
        
        length = self.topo.get_shortest_path_length("R1", "R2")
        self.assertIsNone(length)

    def test_layout_computation(self):
        """Test layout position computation."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        
        pos = self.topo.compute_layout()
        
        self.assertIn("R1", pos)
        self.assertIn("R2", pos)
        self.assertIsInstance(pos["R1"], tuple)
        self.assertEqual(len(pos["R1"]), 2)

    def test_serialization(self):
        """Test topology serialization and deserialization."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 2.5)
        
        # Serialize
        data = self.topo.to_dict()
        
        # Deserialize
        topo2 = NetworkTopology.from_dict(data)
        
        self.assertEqual(len(topo2.routers), 2)
        self.assertEqual(len(topo2.links), 1)
        self.assertEqual(topo2.routers["R1"].name, "R1")
        self.assertEqual(topo2.links["R1-R2"].cost, 2.5)

    def test_copy(self):
        """Test deep copy of topology."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        
        topo2 = self.topo.copy()
        
        # Modify original
        self.topo.add_router("R3")
        
        # Copy should be unchanged
        self.assertEqual(len(topo2.routers), 2)

    def test_get_all_routers_links(self):
        """Test getting all routers and links."""
        r1 = self.topo.add_router("R1")
        r2 = self.topo.add_router("R2")
        self.topo.add_link(r1.id, r2.id, 1.0)
        self.topo.set_link_failed(r1.id, r2.id, True)
        
        all_routers = self.topo.get_all_routers()
        all_links = self.topo.get_all_links()
        active_links = self.topo.get_active_links()
        
        self.assertEqual(len(all_routers), 2)
        self.assertEqual(len(all_links), 1)
        self.assertEqual(len(active_links), 0)


class TestPredefinedScenarios(unittest.TestCase):
    """Test predefined scenario loading."""

    def test_all_scenarios_load(self):
        """Test all predefined scenarios load without error."""
        for scenario_key in list_scenarios():
            topo = load_scenario(scenario_key)
            self.assertIsInstance(topo, NetworkTopology)
            self.assertGreater(len(topo.routers), 0)

    def test_scenario_router_counts(self):
        """Test scenario router/link counts match specification."""
        for scenario_key, info in SCENARIOS.items():
            topo = load_scenario(scenario_key)
            self.assertEqual(len(topo.routers), info['router_count'])
            self.assertEqual(len(topo.get_all_links()), info['link_count'])

    def test_specific_scenarios(self):
        """Test specific scenario structures."""
        # Simple three
        topo = load_scenario("simple_three")
        self.assertEqual(len(topo.routers), 3)
        self.assertEqual(len(topo.get_active_links()), 3)
        self.assertTrue(topo.is_connected())
        
        # Disconnected
        topo = load_scenario("disconnected")
        self.assertEqual(len(topo.routers), 4)
        self.assertFalse(topo.is_connected())


class TestRandomTopology(unittest.TestCase):
    """Test random topology generation."""

    def test_random_topology_basic(self):
        """Test random topology generates correct counts."""
        topo = create_random_topology(5, 7, seed=42)
        
        self.assertEqual(len(topo.routers), 5)
        self.assertEqual(len(topo.get_active_links()), 7)
        self.assertTrue(topo.is_connected())

    def test_random_topology_min_links(self):
        """Test random topology with minimum links (tree)."""
        topo = create_random_topology(5, 4, seed=42)
        
        self.assertEqual(len(topo.routers), 5)
        self.assertEqual(len(topo.get_active_links()), 4)
        self.assertTrue(topo.is_connected())

    def test_random_topology_max_links(self):
        """Test random topology with maximum links (complete graph)."""
        n = 5
        max_links = n * (n - 1) // 2
        topo = create_random_topology(n, max_links, seed=42)
        
        self.assertEqual(len(topo.routers), n)
        self.assertEqual(len(topo.get_active_links()), max_links)
        self.assertTrue(topo.is_connected())

    def test_random_topology_reproducible(self):
        """Test random topology is reproducible with same seed."""
        topo1 = create_random_topology(6, 8, seed=123)
        topo2 = create_random_topology(6, 8, seed=123)
        
        # Should have same structure
        self.assertEqual(set(topo1.links.keys()), set(topo2.links.keys()))
        for key in topo1.links:
            self.assertEqual(topo1.links[key].cost, topo2.links[key].cost)


if __name__ == '__main__':
    unittest.main()