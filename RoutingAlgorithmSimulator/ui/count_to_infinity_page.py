"""
Streamlit UI - Count-to-Infinity Demonstration Page
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from simulation.count_to_infinity import (
    CountToInfinitySimulator, run_classic_count_to_infinity,
    demonstrate_four_node_count_to_infinity, create_count_to_infinity_plot_data,
    explain_count_to_infinity
)
from network.topology import NetworkTopology, create_predefined_scenario


def render_count_to_infinity_page():
    """Render the count-to-infinity demonstration page."""
    st.header(" Count-to-Infinity Problem Demonstration")

    # Explanation
    with st.expander("ℹ About Count-to-Infinity", expanded=True):
        st.markdown("""
**The Count-to-Infinity Problem** is a fundamental issue in Distance Vector routing protocols.

**How it happens:**
1. A link fails, disconnecting a destination
2. Neighbors still believe they can reach the destination through each other
3. They keep increasing the distance metric, "counting to infinity"
4. Eventually the metric reaches "infinity" (16 in RIP) and the route is marked unreachable

**This demonstration shows:**
- Step-by-step distance increases
- Why incorrect routes circulate
- How split horizon and poisoned reverse prevent it
""")

    # Scenario selection
    st.subheader("Select Demonstration Scenario")

    scenario = st.radio(
        "Scenario",
        options=["classic_3node", "four_node"],
        format_func=lambda x: " Classic 3-Node (R1-R2-R3)" if x == "classic_3node"
        else " 4-Node Line (R1-R2-R3-R4)",
        horizontal=True
    )

    # Run demonstration
    if st.button(" Run Count-to-Infinity Demo", type="primary"):
        with st.spinner("Running demonstration..."):
            if scenario == "classic_3node":
                topo = create_predefined_scenario("distance_vector_loop")
                simulator = CountToInfinitySimulator(topo, infinity=16, max_iterations=20)
                result = simulator.run_demonstration(("R2", "R3"))
            else:
                result = demonstrate_four_node_count_to_infinity()

            st.session_state.cti_result = result
            st.session_state.cti_scenario = scenario
            st.success(" Demonstration complete!")

    # Display results
    if 'cti_result' in st.session_state:
        result = st.session_state.cti_result
        display_cti_results(result)

    # Educational explanation
    st.divider()
    st.subheader(" Educational Explanation")

    if 'cti_result' in st.session_state:
        explanation = explain_count_to_infinity(st.session_state.cti_result)
        st.code(explanation, language=None)
    else:
        # Show generic explanation
        st.code(explain_count_to_infinity(None), language=None)

    # Mitigation techniques
    st.divider()
    st.subheader(" Mitigation Techniques")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
**Split Horizon**
- Don't advertise a route back to the neighbor you learned it from
- Prevents 2-node loops
- Simple and effective for basic loops
""")

    with col2:
        st.markdown("""
**Poisoned Reverse**
- Advertise the route back with metric = infinity
- Actively tells neighbor "this route is unreachable via me"
- More robust but uses more bandwidth
""")

    st.markdown("""
**Other Techniques:**
- **Hold-down Timers:** Wait before accepting new route for recently failed destination
- **Triggered Updates:** Send immediate updates on topology change (not just periodic)
- **Route Poisoning:** Explicitly advertise failed routes with infinity metric
""")


def display_cti_results(result):
    """Display count-to-infinity results."""

    # Summary
    st.subheader(" Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Failed Link", f"{result.failed_link[0]}–{result.failed_link[1]}")
    with col2:
        st.metric("Iterations Run", len(result.steps) - 1)
    with col3:
        st.metric("Infinity Value", result.infinity_value)
    with col4:
        status = " Converged" if result.converged else " Max Iterations"
        st.metric("Status", status)

    # Step-by-step table
    st.divider()
    st.subheader(" Distance Evolution by Iteration")

    # Create a comprehensive table
    routers = list(result.topology.routers.keys())
    destinations = [d for d in routers if d != result.failed_link[0] and d != result.failed_link[1]]

    # Show distances for affected destination(s)
    affected_dest = result.failed_link[1]  # The destination that became unreachable

    table_data = []
    for step in result.steps:
        row = {'Iteration': step.iteration}
        for router in routers:
            dist = step.router_distances.get(router, {}).get(affected_dest, result.infinity_value)
            nh = step.router_next_hops.get(router, {}).get(affected_dest, '—')
            row[f"{router} Dist"] = dist if dist < result.infinity_value else '∞'
            row[f"{router} Next Hop"] = nh if nh else '—'
        table_data.append(row)

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Plot
    st.divider()
    st.subheader(" Distance vs Iteration Plot")

    # Plot for each router to the affected destination
    fig, ax = plt.subplots(figsize=(10, 6))

    for router in routers:
        plot_data = create_count_to_infinity_plot_data(result, router, affected_dest)
        iterations = plot_data['iterations']
        distances = plot_data['distances']

        # Filter out None/inf for line plot
        valid = [(i, d) for i, d in zip(iterations, distances) if d < result.infinity_value]
        if valid:
            iters, dists = zip(*valid)
            ax.plot(iters, dists, 'o-', label=f'{router} → {affected_dest}', markersize=4)

        # Mark infinity points
        inf_iters = [i for i, d in zip(iterations, distances) if d >= result.infinity_value]
        if inf_iters:
            ax.scatter(inf_iters, [result.infinity_value]*len(inf_iters),
                       marker='x', s=100, zorder=5)

    ax.axhline(y=result.infinity_value, color='red', linestyle='--', alpha=0.5, label=f'Infinity ({result.infinity_value})')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Distance (Hops)')
    ax.set_title(f'Count-to-Infinity: Distance to {affected_dest} after {result.failed_link[0]}–{result.failed_link[1]} failure')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, result.infinity_value + 2)

    st.pyplot(fig)
    plt.close(fig)

    # Step descriptions
    st.divider()
    st.subheader(" Step Descriptions")

    for step in result.steps:
        with st.expander(f"Iteration {step.iteration}: {step.description[:60]}..."):
            st.write(step.description)

            # Show key distance changes
            if step.iteration > 0:
                prev_step = result.steps[step.iteration - 1]
                for router in routers:
                    curr_dist = step.router_distances.get(router, {}).get(affected_dest)
                    prev_dist = prev_step.router_distances.get(router, {}).get(affected_dest)
                    if curr_dist != prev_dist:
                        st.write(f" {router}: {prev_dist if prev_dist < result.infinity_value else '∞'} → {curr_dist if curr_dist < result.infinity_value else '∞'}")


def render_cti_with_prevention():
    """Render count-to-infinity with prevention mechanisms comparison."""
    st.header(" Count-to-Infinity with Prevention")

    st.info("""
This section would show how Split Horizon and Poisoned Reverse prevent count-to-infinity.
The classic 3-node scenario with R2-R3 link failure:
    - **Without prevention:** R1 and R2 count to infinity for R3
- **With Split Horizon:** R1 doesn't advertise R3 route back to R2 (learned from R2), preventing loop
- **With Poisoned Reverse:** R1 advertises R3 with infinity to R2, immediately breaking loop
""")

    # This would require modifying the DV simulator to support split horizon
    # For now, show the concept
    st.code("""
# Pseudocode for Split Horizon:
for each neighbor N:
    for each destination D:
    if next_hop[D] == N:
    # Don't advertise D to N (simple split horizon)
# OR advertise with infinity (poisoned reverse)
continue
send_update(N, D, distance[D])
""", language="python")