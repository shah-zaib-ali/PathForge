"""
Routing Algorithm Simulator - Main Streamlit Application

A university-level Computer Networks project demonstrating and comparing
Link-State vs Distance-Vector routing algorithms with OSPF validation.

Run with: streamlit run app.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Page configuration
st.set_page_config(
 page_title="Routing Algorithm Simulator",
 page_icon="",
 layout="wide",
 initial_sidebar_state="expanded",
 menu_items={
 'Get Help': None,
 'Report a bug': None,
 'About': """
 # Routing Algorithm Simulator
 
 University-level Computer Networks project demonstrating:
 - Link-State routing (Dijkstra)
 - Distance-Vector routing (Bellman-Ford)
 - RIP simulation
 - Count-to-Infinity demonstration
 - OSPF validation against NetworkX
 """
 }
)

# Custom CSS for better styling
st.markdown("""
<style>
 .main-header {
 font-size: 2.5rem;
 font-weight: 700;
 color: #1f77b4;
 text-align: center;
 margin-bottom: 1rem;
 }
 .sub-header {
 font-size: 1.2rem;
 color: #666;
 text-align: center;
 margin-bottom: 2rem;
 }
 .stMetric {
 background-color: #f0f2f6 !important;
 color: #262730 !important;
 border: 1px solid #e0e0e0 !important;
 border-radius: 0.5rem;
 padding: 1rem;
 }
 .stMetric *,
 .stMetric ::before,
 .stMetric ::after {
 color: #262730 !important;
 }
 [data-testid="stSidebar"] .stMetric {
 background-color: #ffffff !important;
 border: 1px solid #e0e0e0 !important;
 }
 [data-testid="stSidebar"] .stMetric *,
 [data-testid="stSidebar"] .stMetric ::before,
 [data-testid="stSidebar"] .stMetric ::after {
 color: #262730 !important;
 }
 .success-box {
 background-color: #d4edda;
 border: 1px solid #c3e6cb;
 border-radius: 0.5rem;
 padding: 1rem;
 margin: 1rem 0;
 }
 .warning-box {
 background-color: #fff3cd;
 border: 1px solid #ffeeba;
 border-radius: 0.5rem;
 padding: 1rem;
 margin: 1rem 0;
 }
 .error-box {
 background-color: #f8d7da;
 border: 1px solid #f5c6cb;
 border-radius: 0.5rem;
 padding: 1rem;
 margin: 1rem 0;
 }
 
 /* Fix container text visibility - ensure text is dark in light theme */
 .stContainer[border="true"] {
 background-color: #ffffff !important;
 border: 1px solid #e0e0e0 !important;
 border-radius: 0.5rem !important;
 padding: 1rem !important;
 }
 .stContainer[border="true"] * {
 color: #262730 !important;
 }
 .stContainer[border="true"] p,
 .stContainer[border="true"] span,
 .stContainer[border="true"] div,
 .stContainer[border="true"] strong,
 .stContainer[border="true"] em,
 .stContainer[border="true"] a,
 .stContainer[border="true"] li {
 color: #262730 !important;
 }
 
 /* Ensure markdown in containers is visible */
 .stContainer[border="true"] .stMarkdown {
 color: #262730 !important;
 }
 .stContainer[border="true"] .stMarkdown p {
 color: #262730 !important;
 }
 
 /* Fix for streamlit container with border */
 div[data-testid="stContainer"]:has(> div[style*="border"]) {
 background-color: #ffffff !important;
 }
 div[data-testid="stContainer"]:has(> div[style*="border"]) * {
 color: #262730 !important;
 }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
	"""Initialize session state variables."""
	if 'topology' not in st.session_state:
		from network.topology import NetworkTopology
		st.session_state.topology = NetworkTopology()
	if 'topology_name' not in st.session_state:
		st.session_state.topology_name = "Custom"


def load_selected_demo_scenario():
	"""Load the demo scenario chosen in the sidebar dropdown."""
	from network.scenarios import SCENARIOS, load_scenario
	key = st.session_state.get("sidebar_scenario")
	if key in SCENARIOS:
		st.session_state.topology = load_scenario(key)
		st.session_state.topology_name = SCENARIOS[key]["name"]


def render_sidebar():
	"""Render the main navigation sidebar."""
	st.sidebar.markdown("## Routing Algorithm Simulator")
	st.sidebar.divider()

	# Navigation
	pages = {
		" Project Overview": "overview",
		" Network Topology Builder": "topology",
		" Link-State Routing": "link_state",
		" Distance-Vector Routing": "distance_vector",
		" RIP Simulation": "rip",
		" Count-to-Infinity Demo": "count_to_infinity",
		" OSPF Validation": "validation",
		" Performance Comparison": "comparison",
		" Algorithm Theory": "theory",
		" Testing & About": "testing"
	}

	selected = st.sidebar.radio(
		"Navigation",
		options=list(pages.keys()),
		format_func=lambda x: x
	)

	st.sidebar.divider()

	# Quick stats
	if 'topology' in st.session_state:
		topo = st.session_state.topology
		st.sidebar.markdown("### Current Topology")
		st.sidebar.metric("Routers", len(topo.routers))
		st.sidebar.metric("Active Links", len(topo.get_active_links()))
		st.sidebar.metric("Connected", "" if topo.is_connected() else "")
		st.sidebar.caption(f"Name: {st.session_state.get('topology_name', 'Custom')}")

	st.sidebar.divider()
	st.sidebar.markdown("### Quick Actions")

	if st.sidebar.button(" Reset Topology"):
		from network.topology import NetworkTopology
		st.session_state.topology = NetworkTopology()
		st.session_state.topology_name = "Custom"
		st.rerun()

	# Dropdown to choose and load any predefined scenario
	from network.scenarios import SCENARIOS, list_scenarios
	st.sidebar.selectbox(
		"Load Demo Topology",
		options=list_scenarios(),
		format_func=lambda x: SCENARIOS[x]["name"],
		key="sidebar_scenario",
		on_change=load_selected_demo_scenario,
	)
	selected_key = st.session_state.get("sidebar_scenario")
	if selected_key in SCENARIOS:
		st.sidebar.caption(SCENARIOS[selected_key]["description"])

	st.sidebar.divider()
	st.sidebar.caption("FAST NUCES BCS-5B")

	return pages[selected]


def render_overview():
	"""Render the project overview page."""
	st.markdown('<h1 class="main-header"> Routing Algorithm Simulator</h1>', unsafe_allow_html=True)
	st.markdown('<p class="sub-header">Link-State vs Distance-Vector, Validated Against OSPF</p>', unsafe_allow_html=True)

	st.divider()

	# Project description
	col1, col2 = st.columns([2, 1])

	with col1:
		st.markdown("""
 ### Project Overview
 
 This simulator provides an interactive environment for learning and experimenting
 with fundamental routing algorithms used in computer networks.
 
 #### Learning Objectives
 
 - **Understand Link-State routing** through Dijkstra's algorithm visualization
 - **Explore Distance-Vector routing** with iterative Bellman-Ford updates
 - **Experience the Count-to-Infinity problem** in a controlled environment
 - **Compare RIP (hop-count) vs cost-based routing** decisions
 - **Validate algorithm correctness** against NetworkX reference implementation
 - **Analyze convergence behavior** and performance trade-offs
 
 #### Key Features
 
 | Feature | Description |
 |---------|-------------|
 | **Interactive Topology Builder** | Create, modify, and visualize network topologies |
 | **Step-by-Step Algorithms** | Watch Dijkstra and Bellman-Ford execute iteration by iteration |
 | **Multiple Update Strategies** | Synchronous vs asynchronous Distance-Vector updates |
 | **RIP with Loop Prevention** | Split horizon and poisoned reverse demonstrations |
 | **Count-to-Infinity Reproduction** | Classic 3-node and 4-node scenarios with plots |
 | **OSPF Validation** | Automated correctness checking against NetworkX |
 | **Performance Dashboard** | Convergence time, messages, iterations comparison |
 | **Educational Content** | Theory, worked examples, comparison tables |
 """)

	with col2:
		st.markdown("""
 ### Quick Start
 
 1. **Build a Topology** 
 - Go to *Network Topology Builder*
 - Add routers and links, or load a predefined scenario
 
 2. **Run Link-State** 
 - Select a source router
 - Watch Dijkstra's algorithm step-by-step
 - View routing tables and shortest paths
 
 3. **Run Distance-Vector** 
 - Choose synchronous or asynchronous updates
 - Observe convergence over iterations
 - See routing tables evolve
 
 4. **Try RIP** 
 - Enable split horizon/poisoned reverse
 - Compare with cost-based routing
 
 5. **See Count-to-Infinity** 
 - Run the classic 3-node demonstration
 - Watch distances increase to infinity
 
 6. **Validate with OSPF** 
 - Verify Link-State correctness
 - Test after topology changes
 
 7. **Compare Performance** 
 - Run all algorithms on multiple topologies
 - View charts and summary statistics
 """)

	st.divider()

	# Predefined scenarios preview
	st.subheader(" Predefined Scenarios")

	from network.scenarios import SCENARIOS

	scenario_cols = st.columns(4)
	for i, (key, info) in enumerate(SCENARIOS.items()):
		with scenario_cols[i % 4]:
			with st.container(border=True):
				st.markdown(f"**{info['name']}**")
				st.caption(info['description'])
				st.caption(f" {info['router_count']} routers, {info['link_count']} links")

	st.divider()


def main():
	"""Main application entry point."""
	initialize_session_state()
	page = render_sidebar()

	# Route to appropriate page
	if page == "overview":
		render_overview()
	elif page == "topology":
		from ui.topology_page import render_topology_page
		render_topology_page()
	elif page == "link_state":
		from ui.link_state_page import render_link_state_page
		render_link_state_page()
	elif page == "distance_vector":
		from ui.distance_vector_page import render_distance_vector_page
		render_distance_vector_page()
	elif page == "rip":
		from ui.rip_page import render_rip_page
		render_rip_page()
	elif page == "count_to_infinity":
		from ui.count_to_infinity_page import render_count_to_infinity_page
		render_count_to_infinity_page()
	elif page == "validation":
		from ui.validation_page import render_validation_page
		render_validation_page()
	elif page == "comparison":
		from ui.comparison_page import render_comparison_page
		render_comparison_page()
	elif page == "theory":
		from ui.theory_page import render_theory_page
		render_theory_page()
	elif page == "testing":
		from ui.testing_page import render_testing_page
		render_testing_page()


if __name__ == "__main__":
	main()