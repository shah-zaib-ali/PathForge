"""
Streamlit UI - Testing & About Page
"""

import streamlit as st
import subprocess
import sys
import json
from datetime import datetime


def render_testing_page():
    """Render the testing and about page."""
    st.header(" Testing & About")

    tab1, tab2, tab3, tab4 = st.tabs(["Run Tests", "Test Coverage", "About", "System Info"])

    with tab1:
        render_run_tests()

    with tab2:
        render_test_coverage()

    with tab3:
        render_about()

    with tab4:
        render_system_info()


def render_run_tests():
    """Run automated tests."""
    st.subheader(" Run Automated Tests")

    st.markdown("""
Run the test suite using Python's built-in unittest framework.
Tests verify algorithm correctness, not just execution.
""")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(" Run All Tests", type="primary"):
            run_tests_display()

    with col2:
        if st.button(" Run Specific Test Module"):
            test_module = st.selectbox(
                "Select Module",
                ["test_link_state", "test_distance_vector", "test_rip",
                 "test_validation", "test_topology"]
            )
            run_specific_test(test_module)

    # Verbose option
    verbose = st.checkbox("Verbose Output", value=True)
    if verbose:
        st.info("Use `python -m unittest discover -s tests -v` in terminal for full output")


def run_tests_display():
    """Run tests and display results in Streamlit."""
    with st.spinner("Running tests..."):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd="."
            )

            if result.returncode == 0:
                st.success(" All tests passed!")
            else:
                st.error(" Some tests failed")

            # Show output
            with st.expander("Test Output", expanded=True):
                st.code(result.stdout)
            if result.stderr:
                st.code(result.stderr)

        except subprocess.TimeoutExpired:
            st.error("⏱ Tests timed out (120s)")
        except Exception as e:
            st.error(f"Error running tests: {e}")


def run_specific_test(module_name: str):
    """Run a specific test module."""
    with st.spinner(f"Running {module_name}..."):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", f"tests.{module_name}", "-v"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd="."
            )

            if result.returncode == 0:
                st.success(f" {module_name} passed!")
            else:
                st.error(f" {module_name} failed")

            with st.expander("Output"):
                st.code(result.stdout)
            if result.stderr:
                st.code(result.stderr)

        except Exception as e:
            st.error(f"Error: {e}")


def render_test_coverage():
    """Display test coverage information."""
    st.subheader(" Test Coverage")

    test_info = {
        "test_link_state.py": [
            " Dijkstra on simple network",
            " Multiple paths selection",
            " Disconnected destination",
            " Link cost changes",
            " Link failure & recalculation",
            " Step-by-step recording",
            " Empty/single router topologies",
        ],
        "test_distance_vector.py": [
            " DV convergence on connected network",
            " Correct route costs & next hops",
            " Multiple possible paths",
            " Disconnected destination",
            " Link cost changes",
            " Link failure & recalculation",
            " Synchronous vs asynchronous",
            " Count-to-infinity reproducibility",
        ],
        "test_rip.py": [
            " RIP 15-hop maximum",
            " Metric 16 = infinity",
            " Split horizon behavior",
            " Poisoned reverse behavior",
            " RIP vs cost-based comparison",
            " Convergence with loop prevention",
        ],
        "test_validation.py": [
            " OSPF validation against NetworkX",
            " Multiple source routers",
            " Disconnected routers",
            " Route cost & next-hop consistency",
            " Topology change validation",
        ],
        "test_topology.py": [
            " Router add/remove",
            " Link add/remove",
            " Cost updates",
            " Link failure/restore",
            " Invalid inputs (duplicates, self-loops, negative costs)",
            " Predefined scenarios",
            " Random topology generation",
            " Serialization/deserialization",
        ]
    }

    for module, tests in test_info.items():
        with st.expander(f" {module} ({len(tests)} tests)"):
            for test in tests:
                st.write(test)

    st.divider()
    st.write("**Total: ~35 test cases covering all major functionality**")


def render_about():
    """Display project information."""
    st.subheader("ℹ About This Project")

    st.markdown("""
### Routing Algorithm Simulator

**Title:** *Routing Algorithm Simulator: Link-State vs Distance-Vector, Validated Against OSPF*

**Type:** University-level Computer Networks Project

**Purpose:** Educational simulator demonstrating and comparing routing algorithms
used in computer networks, with interactive visualizations and validation.

### Features Implemented

1. ** Network Topology Builder** - Interactive graph editor
2. ** Link-State Routing** - Dijkstra's algorithm with step-by-step visualization
3. ** Distance-Vector Routing** - Bellman-Ford with synchronous/async modes
4. ** RIP Simulation** - Hop-count metric, split horizon, poisoned reverse
5. ** Count-to-Infinity** - Reproducible demonstration with plots
6. ** OSPF Validation** - NetworkX reference comparison
7. ** Performance Comparison** - Metrics, charts, algorithm characteristics
8. ** Educational Content** - Theory, worked examples, comparison tables

### Technology Stack

- **Python 3.8+**
- **Streamlit** - Web interface
- **NetworkX** - Graph operations & reference algorithms
- **pandas** - Data tables & results
- **matplotlib** - Visualizations & charts
- **unittest** - Testing framework

### Algorithms Implemented

- **Dijkstra's Algorithm** (from scratch, not NetworkX wrapper)
- **Bellman-Ford / Distance Vector** (iterative with history)
- **RIP** (hop-count, 15-hop max, split horizon, poisoned reverse)
- **Validation** (against NetworkX shortest_path)

### Author

Developed as a Computer Networks course project demonstrating
routing protocol fundamentals with hands-on experimentation.
""")


def render_system_info():
    """Display system and environment information."""
    st.subheader(" System Information")

    import platform

    info = {
        "Python Version": sys.version.split()[0],
        "Platform": platform.platform(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture()[0],
        "Streamlit Version": st.__version__,
    }

    # Check key packages
    packages = ["networkx", "pandas", "matplotlib", "numpy"]
    for pkg in packages:
        try:
            module = __import__(pkg)
            info[f"{pkg} Version"] = module.__version__
        except (ImportError, AttributeError):
            info[f"{pkg} Version"] = "Not installed"

    for key, value in info.items():
        st.write(f"**{key}:** {value}")

    st.divider()
    st.subheader(" Project Structure")

    structure = """
RoutingAlgorithmSimulator/
├── app.py # Main Streamlit entry point
├── requirements.txt # Python dependencies
├── README.md # Documentation
├── .gitignore # Git ignore rules
├── algorithms/
│ ├── __init__.py
│ ├── link_state.py # Dijkstra implementation
│ ├── distance_vector.py # Bellman-Ford implementation
│ ├── rip.py # RIP simulation
│ └── ospf_validation.py # NetworkX validation
├── network/
│ ├── __init__.py
│ ├── topology.py # Topology management
│ └── scenarios.py # Predefined scenarios
├── simulation/
│ ├── __init__.py
│ ├── convergence.py # Convergence analysis
│ ├── count_to_infinity.py # Count-to-infinity demo
│ └── metrics.py # Performance metrics
├── ui/
│ ├── __init__.py
│ ├── topology_page.py # Topology builder
│ ├── link_state_page.py # Link-State routing
│ ├── distance_vector_page.py # Distance-Vector routing
│ ├── rip_page.py # RIP simulation
│ ├── count_to_infinity_page.py # Count-to-infinity
│ ├── validation_page.py # OSPF validation
│ ├── comparison_page.py # Performance comparison
│ └── theory_page.py # Educational content
└── tests/
├── __init__.py
├── test_link_state.py
├── test_distance_vector.py
├── test_rip.py
├── test_validation.py
└── test_topology.py
"""

    st.code(structure, language="text")