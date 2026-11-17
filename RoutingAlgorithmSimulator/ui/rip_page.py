"""
Streamlit UI - RIP Simulation Page
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from algorithms.rip import (
    run_rip_simulation, compare_rip_modes, demonstrate_rip_vs_cost,
    RIP_INFINITY, RIP_MAX_HOPS
)
from network.topology import NetworkTopology


def render_rip_page():
    """Render the RIP simulation page."""
    st.header(" RIP (Routing Information Protocol) Simulation")

    # Check topology
    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded. Please create or load a topology first.")
        return

    topo = st.session_state.topology

    # RIP info box
    with st.expander("ℹ About RIP Simulation", expanded=False):
        st.markdown(f"""
**RIP Configuration:**
- **Metric:** Hop count (each link = 1 hop)
- **Maximum Hop Count:** {RIP_MAX_HOPS}
- **Infinity (Unreachable):** {RIP_INFINITY}

**Loop Prevention:**
- **Split Horizon:** Don't advertise route back to neighbor you learned it from
- **Poisoned Reverse:** Advertise route back with metric = infinity ({RIP_INFINITY})

*Note: This simulates selected RIP behaviors for educational purposes.
It is not a complete production RIP daemon implementation.*
""")

    # Configuration
    col1, col2 = st.columns(2)
    with col1:
        use_split_horizon = st.checkbox("Enable Split Horizon", value=True)
    with col2:
        use_poisoned_reverse = st.checkbox("Enable Poisoned Reverse", value=False,
                                           disabled=not use_split_horizon)

    max_iter = st.number_input("Max Iterations", min_value=10, max_value=100, value=30)

    # Run button
    if st.button(" Run RIP Simulation", type="primary"):
        with st.spinner("Running RIP simulation..."):
            result = run_rip_simulation(
                topo,
                use_split_horizon=use_split_horizon,
                use_poisoned_reverse=use_poisoned_reverse,
                max_iterations=max_iter,
                record_history=True
            )
        st.session_state.rip_result = result
        st.session_state.rip_config = (use_split_horizon, use_poisoned_reverse)
        st.success(" RIP simulation complete!")

    # Display results
    if 'rip_result' in st.session_state:
        result = st.session_state.rip_result
        display_rip_results(result, topo)

    # Comparison modes
    st.divider()
    st.subheader(" Compare Loop Prevention Mechanisms")

    if st.button("Run All RIP Modes"):
        with st.spinner("Running all modes..."):
            results = compare_rip_modes(topo)
        st.session_state.rip_comparison = results
        st.success(" Comparison complete!")

    if 'rip_comparison' in st.session_state:
        display_rip_comparison(st.session_state.rip_comparison, topo)

    # RIP vs Cost-based comparison
    st.divider()
    st.subheader(" RIP (Hop-Count) vs Link-State (Cost-Based)")

    if st.button("Compare RIP vs Link-State"):
        with st.spinner("Comparing..."):
            comparison = demonstrate_rip_vs_cost(topo)
        st.session_state.rip_vs_ls = comparison
        st.success(" Comparison complete!")

    if 'rip_vs_ls' in st.session_state:
        display_rip_vs_ls_comparison(st.session_state.rip_vs_ls, topo)


def display_rip_results(result, topo: NetworkTopology):
    """Display RIP simulation results."""

    # Convergence info
    st.subheader(" Convergence Information")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status = " Converged" if result.converged else " Max Iterations"
        st.metric("Status", status)
    with col2:
        st.metric("Iterations", result.total_iterations)
    with col3:
        st.metric("Messages", result.total_messages)
    with col4:
        st.metric("Time (ms)", f"{result.computation_time*1000:.2f}")

    # Iteration history
    st.divider()
    st.subheader(" Routing Tables by Iteration")

    if result.iterations:
        iteration = st.slider(
            "Select Iteration",
            0, len(result.iterations) - 1,
            len(result.iterations) - 1,
            key="rip_iter"
        )

        iter_record = result.iterations[iteration]

        # Show changes
        if iter_record.changes:
            st.write(f"**Changes in Iteration {iteration}:**")
            changes_df = pd.DataFrame(iter_record.changes,
                                      columns=['Router', 'Destination', 'Old Hops', 'New Hops'])
            st.dataframe(changes_df, use_container_width=True)
        elif iteration > 0:
            st.info("No changes - converged")

        # Routing tables
        router_tabs = st.tabs([f"{rid} ({topo.routers[rid].name})" for rid in sorted(topo.routers.keys())])

        for i, router_id in enumerate(sorted(topo.routers.keys())):
            with router_tabs[i]:
                table = iter_record.tables.get(router_id)
                if table:
                    table_data = table.to_dict_list()
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)

    # Final tables
    st.divider()
    st.subheader(" Final RIP Routing Tables")

    for router_id in sorted(topo.routers.keys()):
        with st.expander(f"Router {router_id} ({topo.routers[router_id].name})"):
            table = result.final_tables.get(router_id)
            if table:
                table_data = table.to_dict_list()
                if table_data:
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)


def display_rip_comparison(results: dict, topo: NetworkTopology):
    """Display comparison of RIP modes."""

    st.write("**Convergence Comparison:**")

    comparison_data = []
    for mode, result in results.items():
        comparison_data.append({
            'Mode': mode.replace('_', ' ').title(),
            'Iterations': result.total_iterations,
            'Messages': result.total_messages,
            'Converged': "✓" if result.converged else "✗",
            'Time (ms)': f"{result.computation_time*1000:.2f}"
        })

    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)

    # Show differences in final routes
    st.write("**Route Differences:**")

    # Compare none vs split_horizon
    if 'none' in results and 'split_horizon' in results:
        none_result = results['none']
        sh_result = results['split_horizon']

        differences = []
        for router_id in topo.routers:
            none_table = none_result.final_tables.get(router_id)
            sh_table = sh_result.final_tables.get(router_id)
            if none_table and sh_table:
                for dest in none_table.entries:
                    if dest == router_id:
                        continue
                    none_entry = none_table.get_entry(dest)
                    sh_entry = sh_table.get_entry(dest)
                    if none_entry.hops != sh_entry.hops or none_entry.next_hop != sh_entry.next_hop:
                        differences.append({
                            'Router': router_id,
                            'Destination': dest,
                            'No Prevention': f"{none_entry.hops} via {none_entry.next_hop}",
                            'Split Horizon': f"{sh_entry.hops} via {sh_entry.next_hop}"
                        })

        if differences:
            st.write("**Differences: No Prevention vs Split Horizon**")
            st.dataframe(pd.DataFrame(differences), use_container_width=True)
        else:
            st.success("Split Horizon produced same routes as no prevention (no loops in this topology)")


def display_rip_vs_ls_comparison(comparison: dict, topo: NetworkTopology):
    """Display RIP vs Link-State comparison."""

    st.write("**Route Differences (Different Next Hops):**")

    if comparison['differences']:
        diff_df = pd.DataFrame(comparison['differences'])
        st.dataframe(diff_df, use_container_width=True)

        st.info("""
**Explanation:** RIP uses hop count as metric, while Link-State uses link costs.
This can lead to different path selections:
    - RIP prefers fewer hops even if total cost is higher
- Link-State prefers lower total cost even if more hops
""")
    else:
        st.success("RIP and Link-State selected the same next hops for all destinations.")

    # Show side-by-side for a router
    routers = list(topo.routers.keys())
    if routers:
        selected_router = st.selectbox(
            "View Details for Router",
            routers,
            format_func=lambda x: f"{x} ({topo.routers[x].name})"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.write("**RIP Routes (Hop Count)**")
            rip_routes = comparison['rip'].get(selected_router, {})
            if rip_routes:
                rip_data = []
                for dest, info in rip_routes.items():
                    rip_data.append({
                        'Destination': dest,
                        'Next Hop': info['next_hop'],
                        'Hops': info['hops'],
                        'Path': ' → '.join(info['path'])
                    })
                st.dataframe(pd.DataFrame(rip_data), use_container_width=True)
            else:
                st.info("No routes")

        with col2:
            st.write("**Link-State Routes (Cost)**")
            ls_routes = comparison['link_state'].get(selected_router, {})
            if ls_routes:
                ls_data = []
                for dest, info in ls_routes.items():
                    ls_data.append({
                        'Destination': dest,
                        'Next Hop': info['next_hop'],
                        'Cost': f"{info['cost']:.1f}",
                        'Path': ' → '.join(info['path'])
                    })
                st.dataframe(pd.DataFrame(ls_data), use_container_width=True)
            else:
                st.info("No routes")