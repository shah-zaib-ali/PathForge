"""
Streamlit UI - OSPF Validation Page
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.ospf_validation import (
    OSPFValidator, validate_link_state, OSPFValidationReport
)
from network.topology import NetworkTopology


def render_validation_page():
    """Render the OSPF validation page."""
    st.header(" OSPF Validation - Link-State vs NetworkX Reference")

    # Check topology
    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded. Please create or load a topology first.")
        return

    topo = st.session_state.topology

    # Info
    with st.expander("ℹ About OSPF Validation", expanded=False):
        st.markdown("""
**Purpose:** Validate that our Link-State (Dijkstra) implementation produces
correct shortest paths by comparing against NetworkX's reference implementation.

**What is checked:**
- Path costs (distances) match exactly
- Next-hop routers match
- Full paths match
- Unreachable destinations correctly identified

**Note:** This validates algorithmic correctness, not interoperability
with a real OSPF daemon like FRRouting.
""")

    # Validation options
    col1, col2 = st.columns(2)
    with col1:
        validate_all = st.checkbox("Validate All Routers", value=True)
    with col2:
        if not validate_all:
            source_router = st.selectbox(
                "Source Router",
                options=list(topo.routers.keys()),
                format_func=lambda x: f"{x} ({topo.routers[x].name})"
            )

    # Run validation
    if st.button(" Run Validation", type="primary"):
        with st.spinner("Validating against NetworkX reference..."):
            if validate_all:
                report = validate_link_state(topo)
            else:
                validator = OSPFValidator(topo)
                report = validator.validate_all(sources=[source_router])

        st.session_state.validation_report = report
        st.success(" Validation complete!")

    # Display results
    if 'validation_report' in st.session_state:
        report = st.session_state.validation_report
        display_validation_report(report, topo)

    # Topology change validation
    st.divider()
    st.subheader(" Validate After Topology Change")

    st.write("Modify the topology in the **Network Topology Builder** page, then run validation again to verify recalculation correctness.")


def display_validation_report(report: OSPFValidationReport, topo: NetworkTopology):
    """Display validation report."""

    # Overall summary
    st.subheader(" Overall Results")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tests", report.overall_total)
    with col2:
        st.metric("Passed", report.overall_passed)
    with col3:
        st.metric("Failed", report.overall_total - report.overall_passed)
    with col4:
        color = "green" if report.overall_pass_rate == 1.0 else "red"
        st.metric("Pass Rate", f"{report.overall_pass_rate:.1%}")

    if report.overall_pass_rate == 1.0:
        st.success(" All validations passed! Link-State implementation is correct.")
    else:
        st.error(f" {report.overall_total - report.overall_passed} validation(s) failed.")

    st.metric("Validation Time", f"{report.computation_time*1000:.2f} ms")

    # Per-router summary
    st.divider()
    st.subheader(" Per-Router Summary")

    router_summary = []
    for router_id, summary in report.router_summaries.items():
        router_summary.append({
            'Router': f"{router_id} ({topo.routers[router_id].name})",
            'Tests': summary.total_tests,
            'Passed': summary.passed,
            'Failed': summary.failed,
            'Pass Rate': f"{summary.pass_rate:.1%}"
        })

    st.dataframe(pd.DataFrame(router_summary), use_container_width=True)

    # Detailed results
    st.divider()
    st.subheader(" Detailed Validation Results")

    # Filter options
    show_only_failures = st.checkbox("Show Only Failures", value=False)

    rows = report.to_dataframe_rows()
    if show_only_failures:
        rows = [r for r in rows if r['Status'] == ' FAIL']

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            " Download Results as CSV",
            csv,
            file_name=f"ospf_validation_{st.session_state.get('topology_name', 'topology')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No results to display")

    # Mismatches detail
    if report.mismatches:
        st.divider()
        st.subheader(" Mismatch Details")

        for mismatch in report.mismatches:
            with st.expander(f" {mismatch.source} → {mismatch.destination} ({mismatch.mismatch_type})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Expected (NetworkX):**")
                    st.write(f" Distance: {mismatch.expected_distance if mismatch.expected_distance != float('inf') else '∞'}")
                    st.write(f" Next Hop: {mismatch.expected_next_hop or '—'}")
                    st.write(f" Path: {' → '.join(mismatch.expected_path) if mismatch.expected_path else 'Unreachable'}")
                with col2:
                    st.write("**Actual (Simulator):**")
                    st.write(f" Distance: {mismatch.actual_distance if mismatch.actual_distance != float('inf') else '∞'}")
                    st.write(f" Next Hop: {mismatch.actual_next_hop or '—'}")
                    st.write(f" Path: {' → '.join(mismatch.actual_path) if mismatch.actual_path else 'Unreachable'}")


def render_frr_integration_info():
    """Render information about FRRouting integration."""
    st.header(" FRRouting Integration (Optional)")

    st.markdown("""
### Real OSPF Daemon Validation

For production-grade validation, you can compare against **FRRouting (FRR)**,
a full-featured routing protocol daemon that implements OSPF, RIP, BGP, and more.

**Integration Approach:**
1. Deploy FRR in a Docker container or VM
2. Configure OSPF with the same topology
3. Extract routing tables via `vtysh` or JSON API
4. Compare with simulator results

**Example Docker Setup:**
```bash
docker run -d --name frr --privileged -v ./frr.conf:/etc/frr/frr.conf frrouting/frr
```

**FRR Configuration (frr.conf):**
```
frr version 8.0
router ospf
network 10.0.0.0/8 area 0.0.0.0
```

**Limitations:**
- Requires Docker/container runtime
- More complex setup
- Network namespace configuration needed
- Not required for educational validation (NetworkX is sufficient)
""")

    if st.button("Check FRR Availability"):
        import subprocess
        try:
            result = subprocess.run(['docker', 'version'], capture_output=True, text=True)
            if result.returncode == 0:
                st.success(" Docker is available")
            else:
                st.warning(" Docker not available")
        except FileNotFoundError:
            st.warning(" Docker not installed")