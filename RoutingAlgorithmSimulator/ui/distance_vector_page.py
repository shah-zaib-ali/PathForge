"""
Streamlit UI - Distance-Vector Routing Page
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.distance_vector import (
    run_distance_vector, DistanceVectorResult, UpdateStrategy, DVIterationRecord
)
from network.topology import NetworkTopology


def render_distance_vector_page():
    """Render the Distance-Vector routing page."""
    st.header(" Distance-Vector Routing (Bellman-Ford)")

    # Check topology
    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded. Please create or load a topology first.")
        return

    topo = st.session_state.topology

    # Configuration
    col1, col2 = st.columns(2)
    with col1:
        strategy = st.radio(
            "Update Strategy",
            options=["synchronous", "asynchronous"],
            format_func=lambda x: " Synchronous (all routers update simultaneously)" if x == "synchronous"
            else " Asynchronous (random order each round)",
            horizontal=False
        )

    with col2:
        max_iter = st.number_input("Max Iterations", min_value=10, max_value=200, value=50)

    # Run button
    if st.button(" Run Distance-Vector Simulation", type="primary"):
        with st.spinner("Running Distance-Vector algorithm..."):
            strat = UpdateStrategy.SYNCHRONOUS if strategy == "synchronous" else UpdateStrategy.ASYNCHRONOUS
            result = run_distance_vector(topo, strat, max_iterations=max_iter, record_history=True)
            st.session_state.dv_result = result
            st.session_state.dv_strategy = strategy
            st.success(" Simulation complete!")

    # Display results
    if 'dv_result' in st.session_state:
        result = st.session_state.dv_result
        display_dv_results(result, topo)


def display_dv_results(result: DistanceVectorResult, topo: NetworkTopology):
    """Display Distance-Vector simulation results."""

    # Convergence info
    st.subheader(" Convergence Information")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = " Converged" if result.converged else " Max Iterations Reached"
        st.metric("Status", status)
    with col2:
        st.metric("Iterations", result.total_iterations)
    with col3:
        st.metric("Messages Exchanged", result.total_messages)
    with col4:
        st.metric("Computation Time", f"{result.computation_time*1000:.2f} ms")

    if result.max_iterations_reached:
        st.warning(" Maximum iterations reached without convergence. This may indicate a routing loop or count-to-infinity.")

    # Routing tables at each iteration
    st.divider()
    st.subheader(" Routing Tables by Iteration")

    if result.iterations:
        iteration = st.slider(
            "Select Iteration",
            0, len(result.iterations) - 1,
            len(result.iterations) - 1,
            help="View routing tables at each iteration"
        )

        iter_record = result.iterations[iteration]

        # Show changes in this iteration
        if iter_record.changes:
            st.write(f"**Changes in Iteration {iteration}:**")
            changes_df = pd.DataFrame(iter_record.changes,
                                      columns=['Router', 'Destination', 'Old Distance', 'New Distance'])
            st.dataframe(changes_df, use_container_width=True)
        elif iteration > 0:
            st.info("No changes - algorithm converged")

        # Routing tables for each router
        router_tabs = st.tabs([f"{rid} ({topo.routers[rid].name})" for rid in sorted(topo.routers.keys())])

        for i, router_id in enumerate(sorted(topo.routers.keys())):
            with router_tabs[i]:
                table = iter_record.tables.get(router_id)
                if table:
                    table_data = table.to_dict_list()
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("No routes (single router topology)")

    # Convergence visualization
    st.divider()
    st.subheader(" Convergence Visualization")

    # Select route to visualize
    routers = list(topo.routers.keys())
    if len(routers) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            src = st.selectbox("Source Router", routers, format_func=lambda x: f"{x} ({topo.routers[x].name})", key="dv_src")
        with col2:
            dst = st.selectbox("Destination Router", routers, format_func=lambda x: f"{x} ({topo.routers[x].name})", key="dv_dst")

        if src != dst:
            plot_convergence(result, src, dst)

    # Final routing tables summary
    st.divider()
    st.subheader(" Final Routing Tables (All Routers)")

    for router_id in sorted(topo.routers.keys()):
        with st.expander(f"Router {router_id} ({topo.routers[router_id].name})"):
            table = result.final_tables.get(router_id)
            if table:
                table_data = table.to_dict_list()
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)


def plot_convergence(result: DistanceVectorResult, source: str, destination: str):
    """Plot distance convergence over iterations."""
    fig, ax = plt.subplots(figsize=(10, 5))

    iterations = []
    distances = []
    next_hops = []

    for rec in result.iterations:
        table = rec.tables.get(source)
        if table:
            entry = table.get_entry(destination)
            iterations.append(rec.iteration)
            dist = entry.distance
            distances.append(dist if dist != float('inf') else None)
            next_hops.append(entry.next_hop)

    # Plot distances
    valid_points = [(i, d) for i, d in zip(iterations, distances) if d is not None]
    if valid_points:
        iters, dists = zip(*valid_points)
        ax.plot(iters, dists, 'b-o', label='Distance', markersize=4)

    # Mark infinity points
    inf_points = [i for i, d in zip(iterations, distances) if d is None]
    if inf_points:
        ax.scatter(inf_points, [max([d for d in distances if d is not None], default=10)*1.1]*len(inf_points),
                   color='red', marker='x', s=100, label='Unreachable (∞)', zorder=5)

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Distance')
    ax.set_title(f'Convergence: {source} → {destination}')
    ax.legend()
    ax.grid(True, alpha=0.3)

    st.pyplot(fig)
    plt.close(fig)

    # Next hop changes
    if len(set(next_hops)) > 1:
        st.write("**Next Hop Changes:**")
        for i, (it, nh) in enumerate(zip(iterations, next_hops)):
            if i == 0 or nh != next_hops[i-1]:
                st.write(f" Iteration {it}: Next hop = {nh if nh else '—'}")


def render_dv_comparison_page():
    """Render comparison between synchronous and asynchronous."""
    st.header(" Synchronous vs Asynchronous Comparison")

    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded.")
        return

    topo = st.session_state.topology

    if st.button("Run Both Strategies"):
        with st.spinner("Running synchronous..."):
            sync_result = run_distance_vector(topo, UpdateStrategy.SYNCHRONOUS, record_history=True)
        with st.spinner("Running asynchronous..."):
            async_result = run_distance_vector(topo, UpdateStrategy.ASYNCHRONOUS, record_history=True)

        st.session_state.dv_sync = sync_result
        st.session_state.dv_async = async_result

    if 'dv_sync' in st.session_state and 'dv_async' in st.session_state:
        sync = st.session_state.dv_sync
        async_ = st.session_state.dv_async

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(" Synchronous")
            st.metric("Iterations", sync.total_iterations)
            st.metric("Messages", sync.total_messages)
            st.metric("Time (ms)", f"{sync.computation_time*1000:.2f}")
            st.metric("Converged", "✓" if sync.converged else "✗")

        with col2:
            st.subheader(" Asynchronous")
            st.metric("Iterations", async_.total_iterations)
            st.metric("Messages", async_.total_messages)
            st.metric("Time (ms)", f"{async_.computation_time*1000:.2f}")
            st.metric("Converged", "✓" if async_.converged else "✗")

        # Compare final routes
        st.subheader("Route Comparison")
        differences = []
        for router_id in topo.routers:
            sync_table = sync.final_tables.get(router_id)
            async_table = async_.final_tables.get(router_id)
            if sync_table and async_table:
                for dest in sync_table.entries:
                    if dest == router_id:
                        continue
                    sync_entry = sync_table.get_entry(dest)
                    async_entry = async_table.get_entry(dest)
                    if sync_entry.distance != async_entry.distance or sync_entry.next_hop != async_entry.next_hop:
                        differences.append({
                            'Router': router_id,
                            'Destination': dest,
                            'Sync Distance': sync_entry.distance,
                            'Async Distance': async_entry.distance,
                            'Sync Next Hop': sync_entry.next_hop,
                            'Async Next Hop': async_entry.next_hop
                        })

        if differences:
            st.dataframe(pd.DataFrame(differences), use_container_width=True)
        else:
            st.success("Both strategies produced identical routes!")