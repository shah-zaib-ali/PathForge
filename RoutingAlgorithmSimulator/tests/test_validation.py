"""
Tests for OSPF Validation Module
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.ospf_validation import (
    OSPFValidator, validate_link_state, OSPFValidationReport,
    RouterValidationSummary, ValidationResult
)
from network.topology import NetworkTopology, create_predefined_scenario


class TestOSPFValidation(unittest.TestCase):
    """Test cases for OSPF validation against NetworkX."""

    def setUp(self):
        """Set up test topologies."""
        self.simple_topo = create_predefined_scenario("simple_three")
        self.multi_path_topo = create_predefined_scenario("multiple_paths")
        self.cost_vs_hops_topo = create_predefined_scenario("cost_vs_hops")
        self.disconnected_topo = create_predefined_scenario("disconnected")
        self.larger_topo = create_predefined_scenario("larger_network")

    def test_validation_simple_three(self):
        """Test validation on simple 3-router network."""
        report = validate_link_state(self.simple_topo)
        
        self.assertIsInstance(report, OSPFValidationReport)
        self.assertEqual(report.overall_total, 6)  # 3 routers * 2 destinations each
        self.assertEqual(report.overall_passed, 6)
        self.assertEqual(report.overall_pass_rate, 1.0)
        self.assertEqual(len(report.mismatches), 0)
        self.assertEqual(len(report.router_summaries), 3)

    def test_validation_multiple_paths(self):
        """Test validation on multi-path network."""
        report = validate_link_state(self.multi_path_topo)
        
        self.assertEqual(report.overall_pass_rate, 1.0)
        self.assertEqual(len(report.mismatches), 0)
        
        # Check all routers validated
        self.assertEqual(len(report.router_summaries), 5)

    def test_validation_cost_vs_hops(self):
        """Test validation on cost vs hops topology."""
        report = validate_link_state(self.cost_vs_hops_topo)
        
        self.assertEqual(report.overall_pass_rate, 1.0)
        self.assertEqual(len(report.mismatches), 0)

    def test_validation_disconnected(self):
        """Test validation handles disconnected components."""
        report = validate_link_state(self.disconnected_topo)
        
        # Should still validate correctly (unreachable = unreachable)
        self.assertEqual(report.overall_pass_rate, 1.0)
        self.assertEqual(len(report.mismatches), 0)

    def test_validation_larger_network(self):
        """Test validation on larger network."""
        report = validate_link_state(self.larger_topo)
        
        self.assertEqual(report.overall_pass_rate, 1.0)
        self.assertEqual(len(report.mismatches), 0)
        self.assertEqual(len(report.router_summaries), 8)

    def test_validation_single_source(self):
        """Test validation for single source router."""
        validator = OSPFValidator(self.simple_topo)
        report = validator.validate_all(sources=["R1"])
        
        self.assertEqual(len(report.router_summaries), 1)
        self.assertIn("R1", report.router_summaries)
        self.assertEqual(report.router_summaries["R1"].total_tests, 2)

    def test_validation_report_structure(self):
        """Test validation report has correct structure."""
        report = validate_link_state(self.simple_topo)
        
        # Check router summaries
        for router_id, summary in report.router_summaries.items():
            self.assertIsInstance(summary, RouterValidationSummary)
            self.assertEqual(summary.router_id, router_id)
            self.assertGreater(summary.total_tests, 0)
            self.assertEqual(summary.passed + summary.failed, summary.total_tests)
            self.assertAlmostEqual(summary.pass_rate, summary.passed / summary.total_tests)
            
            # Check individual results
            for result in summary.results:
                self.assertIsInstance(result, ValidationResult)
                self.assertEqual(result.source, router_id)
                self.assertIn('passed', result.__dict__)

    def test_validation_dataframe_export(self):
        """Test validation report can be converted to DataFrame rows."""
        report = validate_link_state(self.simple_topo)
        rows = report.to_dataframe_rows()
        
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), report.overall_total)
        
        for row in rows:
            self.assertIn('Source Router', row)
            self.assertIn('Destination', row)
            self.assertIn('Expected Cost', row)
            self.assertIn('Actual Cost', row)
            self.assertIn('Expected Next Hop', row)
            self.assertIn('Actual Next Hop', row)
            self.assertIn('Expected Path', row)
            self.assertIn('Actual Path', row)
            self.assertIn('Status', row)
            self.assertIn('Mismatch', row)

    def test_validate_single_pair(self):
        """Test single pair validation."""
        validator = OSPFValidator(self.simple_topo)
        result = validator.validate_single_pair("R1", "R3")
        
        self.assertIsInstance(result, ValidationResult)
        self.assertEqual(result.source, "R1")
        self.assertEqual(result.destination, "R3")
        self.assertTrue(result.passed)
        self.assertEqual(result.mismatch_type, "")

    def test_mismatch_detection(self):
        """Test that mismatches would be detected (simulated)."""
        # This test verifies the mismatch detection logic
        # by checking the comparison functions directly
        validator = OSPFValidator(self.simple_topo)
        
        # Test distance comparison
        self.assertTrue(validator._compare_distances(5.0, 5.0))
        self.assertTrue(validator._compare_distances(float('inf'), float('inf')))
        self.assertFalse(validator._compare_distances(5.0, float('inf')))
        self.assertFalse(validator._compare_distances(float('inf'), 5.0))
        self.assertTrue(validator._compare_distances(5.0, 5.0000000001))  # Float tolerance
        
        # Test path comparison
        self.assertTrue(validator._compare_paths(["R1", "R2", "R3"], ["R1", "R2", "R3"]))
        self.assertFalse(validator._compare_paths(["R1", "R2", "R3"], ["R1", "R3"]))
        self.assertTrue(validator._compare_paths([], []))

    def test_validation_after_topology_change(self):
        """Test validation works after topology modification."""
        from algorithms.ospf_validation import validate_after_topology_change
        
        # Modify topology
        modified_topo = self.simple_topo.copy()
        modified_topo.update_link_cost("R1", "R3", 1.0)
        
        report = validate_after_topology_change(self.simple_topo, modified_topo)
        
        self.assertEqual(report.overall_pass_rate, 1.0)


class TestValidationEdgeCases(unittest.TestCase):
    """Test edge cases for validation."""

    def test_single_router_validation(self):
        """Test validation with single router."""
        topo = NetworkTopology()
        topo.add_router("R1")
        
        report = validate_link_state(topo)
        
        self.assertEqual(report.overall_total, 0)
        self.assertEqual(report.overall_passed, 0)
        self.assertEqual(report.overall_pass_rate, 1.0)

    def test_two_router_validation(self):
        """Test validation with two routers."""
        topo = NetworkTopology()
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        topo.add_link(r1.id, r2.id, 5.0)
        
        report = validate_link_state(topo)
        
        self.assertEqual(report.overall_total, 2)  # R1->R2, R2->R1
        self.assertEqual(report.overall_passed, 2)
        self.assertEqual(report.overall_pass_rate, 1.0)


if __name__ == '__main__':
    unittest.main()