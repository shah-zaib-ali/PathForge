"""
Streamlit UI - Link-State Routing Page
"""

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from algorithms.link_state import LinkStateRouter, LinkStateResult, DijkstraStep, run_link_state_for_all_routers
from network.topology import NetworkTopology


def render_link_state_page():
    """Render the Link-State routing page."""
    st.header(" Link-State Routing (Dijkstra's Algorithm)")

    # Check if topology exists
    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded. Please create or load a topology first.")
        return

    topo = st.session_state.topology

    # Source router selection
    col1, col2 = st.columns([1, 3])
    with col1:
        source_id = st.selectbox(
        "Source Router",
        options=list(topo.routers.keys()),
        format_func=lambda x: f"{x} ({topo.routers[x].name})"
        )

    with col2:
        st.write(f"**Topology:** {st.session_state.get('topology_name', 'Custom')} | "
        f"Routers: {len(topo.routers)} | Links: {len(topo.get_active_links())}")

    # Run button
    if st.button(" Compute Shortest Paths", type="primary"):
        with st.spinner("Running Dijkstra's algorithm..."):
            router = LinkStateRouter(topo)
            result = router.compute_shortest_paths(source_id, record_steps=True)
            st.session_state.ls_result = result
            st.session_state.ls_source = source_id
            st.success(" Computation complete!")

    # Display results if available
    if 'ls_result' in st.session_state and st.session_state.ls_source == source_id:
        result = st.session_state.ls_result
        display_link_state_results(result, topo, source_id)

    # Run for all routers
    st.divider()
    if st.button(" Compute for All Routers"):
        with st.spinner("Computing for all routers..."):
            results = run_link_state_for_all_routers(topo, record_steps=False)
            st.session_state.ls_all_results = results
            st.success(" All routers computed!")

    if 'ls_all_results' in st.session_state:
        display_all_routers_results(st.session_state.ls_all_results, topo)


def display_link_state_results(result: LinkStateResult, topo: NetworkTopology, source_id: str):
    """Display detailed Link-State results."""

    # Routing table
    st.subheader(f" Routing Table for {source_id} ({topo.routers[source_id].name})")

    table_data = result.get_routing_table()
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No other routers in topology")

    # Path visualization
    st.subheader(" Shortest Paths Visualization")

    # Destination selector for path highlight
    dest_options = [d for d in result.paths.keys() if d != source_id and result.paths[d]]
    if dest_options:
        selected_dest = st.selectbox(
        "Highlight Path To",
        options=dest_options,
        format_func=lambda x: f"{x} ({topo.routers[x].name}) - Cost: {result.distances[x]:.1f}"
        )

        fig = draw_topology_with_paths(topo, result, source_id, selected_dest)
        st.pyplot(fig)
        plt.close(fig)

    # Step-by-step Dijkstra
    st.divider()
    st.subheader(" Dijkstra's Algorithm - Step by Step")

    if result.steps:
        step_idx = st.slider("Step", 0, len(result.steps) - 1, len(result.steps) - 1,
        help="Slide to see algorithm progression")

        step = result.steps[step_idx]

        col1, col2 = st.columns([1, 1])

        with col1:
            st.write(f"**Iteration {step.iteration}**")
            st.write(step.description)

            st.write("**Visited Nodes:**", ', '.join(sorted(step.visited)) if step.visited else 'None')

            if step.current_node:
                st.write(f"**Current Node:** {step.current_node}")

        with col2:
            # Tentative distances table
            dist_data = []
            for node in sorted(topo.routers.keys()):
                dist = step.tentative_distances.get(node, float('inf'))
                pred = step.predecessors.get(node)
                status = "Visited" if node in step.visited else "Unvisited"
                if node == step.current_node:
                    status = "Current"

                dist_data.append({
                'Node': node,
                'Name': topo.routers[node].name,
                'Distance': dist if dist != float('inf') else '∞',
                'Predecessor': pred if pred else '—',
                'Status': status
                })

            df = pd.DataFrame(dist_data)
            st.dataframe(df, use_container_width=True)

            # Priority queue state
            if step.priority_queue:
                st.write("**Priority Queue:**")
                pq_data = [{'Distance': d, 'Node': n} for d, n in sorted(step.priority_queue)]
                st.dataframe(pd.DataFrame(pq_data), use_container_width=True)

    # Performance info
    st.divider()
    st.subheader(" Performance")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Computation Time", f"{result.computation_time*1000:.2f} ms")
    with col2:
        st.metric("Routers", len(topo.routers))
    with col3:
        st.metric("Links", len(topo.get_active_links()))


def display_all_routers_results(results: dict, topo: NetworkTopology):
    """Display results for all routers."""
    st.subheader(" All Routers Routing Tables")

    # Create combined view
    all_destinations = sorted(topo.routers.keys())

    for source_id in sorted(results.keys()):
        result = results[source_id]
        with st.expander(f"Router {source_id} ({topo.routers[source_id].name})"):
            table_data = result.get_routing_table()
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)


def draw_topology_with_paths(topo: NetworkTopology, result: LinkStateResult,
source_id: str, dest_id: str) -> plt.Figure:
    """Draw topology with shortest path highlighted."""
    fig, ax = plt.subplots(figsize=(10, 7))

    pos = topo.get_layout()
    path = result.paths.get(dest_id, [])

    # Draw all edges (faded)
    for link in topo.get_all_links():
        src_pos = pos.get(link.source, (0, 0))
        tgt_pos = pos.get(link.target, (0, 0))

        color = 'red' if link.is_failed else 'lightgray'
        style = '--' if link.is_failed else '-'
        width = 1

        ax.plot([src_pos[0], tgt_pos[0]], [src_pos[1], tgt_pos[1]],
        color=color, linestyle=style, linewidth=width, zorder=1)

        # Label with cost
        mid_x = (src_pos[0] + tgt_pos[0]) / 2
        mid_y = (src_pos[1] + tgt_pos[1]) / 2
        ax.text(mid_x, mid_y, f"{link.cost}", fontsize=8, ha='center', va='center',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.6),
        zorder=2)

    # Highlight shortest path edges
    if len(path) >= 2:
        path_edges = set()
        for i in range(len(path) - 1):
            u, v = path[i], path[i+1]
            path_edges.add((u, v))
            path_edges.add((v, u))

        for link in topo.get_active_links():
            if (link.source, link.target) in path_edges or (link.target, link.source) in path_edges:
                src_pos = pos[link.source]
                tgt_pos = pos[link.target]
                ax.plot([src_pos[0], tgt_pos[0]], [src_pos[1], tgt_pos[1]],
                color='blue', linewidth=3, zorder=3)

                mid_x = (src_pos[0] + tgt_pos[0]) / 2
                mid_y = (src_pos[1] + tgt_pos[1]) / 2
                ax.text(mid_x, mid_y, f"{link.cost}", fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', edgecolor='blue', alpha=0.9),
                zorder=4)

    # Draw nodes
    for rid, router in topo.routers.items():
        x, y = pos.get(rid, (0, 0))

        if rid == source_id:
            color = 'green'
            label = f"{router.name} (SRC)"
        elif rid == dest_id:
            color = 'red'
            label = f"{router.name} (DST)"
        elif rid in path:
            color = 'yellow'
            label = router.name
        else:
            color = 'lightblue'
            label = router.name

        circle = plt.Circle((x, y), 0.08, color=color, ec='black', linewidth=2, zorder=5)
        ax.add_patch(circle)
        ax.text(x, y, router.name, ha='center', va='center', fontsize=10, fontweight='bold', zorder=6)

        # Add label below
        ax.text(x, y - 0.12, label, ha='center', va='top', fontsize=8, zorder=6)

    # Path info
    if path:
        path_str = ' → '.join([topo.routers[n].name for n in path])
        cost = result.distances[dest_id]
        ax.set_title(f"Shortest Path: {path_str} (Cost: {cost:.1f})", fontsize=14, pad=20)
    else:
        ax.set_title(f"No path from {topo.routers[source_id].name} to {topo.routers[dest_id].name}", fontsize=14, pad=20)

    ax.set_aspect('equal')
    ax.axis('off')

    return fig
