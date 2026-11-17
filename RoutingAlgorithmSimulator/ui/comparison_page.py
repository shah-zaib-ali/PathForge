"""
Streamlit UI - Performance Comparison Page
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from simulation.metrics import MetricsCollector, run_full_comparison, generate_metrics_summary
from network.scenarios import list_scenarios, load_scenario
from network.topology import NetworkTopology


def render_comparison_page():
    """Render the performance comparison page."""
    st.header(" Performance Comparison Dashboard")

    # Info
    with st.expander("ℹ About Performance Comparison", expanded=False):
        st.markdown("""
**Metrics Measured:**
- **Convergence Time:** Wall-clock time for algorithm to complete
- **Iterations:** Number of update rounds until convergence
- **Messages:** Simulated routing messages exchanged
- **Path Cost:** Average shortest-path cost (Link-State) or hop count (RIP)
- **Correctness:** Whether routes match Link-State reference

**Notes:**
- Execution time depends on machine, Python overhead, and simulation design
- Message counts are simulated, not actual network packets
- Results are for educational comparison, not production benchmarking
""")

    # Scenario selection
    st.subheader("Select Topologies to Compare")

    available_scenarios = list_scenarios()
    scenario_info = {k: f"{k} ({v['router_count']}R, {v['link_count']}L)" for k, v in
                     {s: __import__('network.scenarios', fromlist=['SCENARIOS']).SCENARIOS[s] for s in available_scenarios}.items()}

    selected = st.multiselect(
        "Scenarios",
        options=available_scenarios,
        default=["simple_three", "multiple_paths", "cost_vs_hops", "larger_network"],
        format_func=lambda x: scenario_info[x]
    )

    # Run comparison
    if st.button(" Run Comparison", type="primary"):
        if not selected:
            st.error("Please select at least one scenario")
        else:
            with st.spinner("Running algorithms on selected topologies..."):
                collector = MetricsCollector()
                for scenario_key in selected:
                    topo = load_scenario(scenario_key)
                    scenario_name = __import__('network.scenarios', fromlist=['SCENARIOS']).SCENARIOS[scenario_key]['name']
                    collector.compare_on_topology(topo, scenario_name)

            st.session_state.metrics_collector = collector
            st.success(" Comparison complete!")

    # Display results
    if 'metrics_collector' in st.session_state:
        collector = st.session_state.metrics_collector
        display_comparison_results(collector)

    # Quick single-topology comparison
    st.divider()
    st.subheader(" Quick Comparison (Current Topology)")

    if 'topology' in st.session_state and st.session_state.topology.routers:
        if st.button("Compare on Current Topology"):
            with st.spinner("Running comparison..."):
                collector = MetricsCollector()
                collector.compare_on_topology(
                    st.session_state.topology,
                    st.session_state.get('topology_name', 'Current')
                )
            st.session_state.metrics_collector = collector
            st.success(" Done!")
    else:
        st.info("Load a topology first to run quick comparison")


def display_comparison_results(collector: MetricsCollector):
    """Display comparison results with charts."""

    # Summary table
    st.subheader(" Results Summary")

    rows = collector.get_summary_dataframe()
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    # Download
    csv = df.to_csv(index=False)
    st.download_button(
        " Download as CSV",
        csv,
        file_name="routing_comparison_results.csv",
        mime="text/csv"
    )

    # Charts
    st.divider()
    st.subheader(" Visualizations")

    # Prepare data for plotting
    plot_df = df.copy()

    # Convergence Time Chart
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Convergence Time
    ax = axes[0, 0]
    for alg in plot_df['Algorithm'].unique():
        alg_data = plot_df[plot_df['Algorithm'] == alg]
        ax.bar([f"{row['Topology']}\n{alg}" for _, row in alg_data.iterrows()],
               alg_data['Convergence Time (ms)'], label=alg, alpha=0.7)
    ax.set_ylabel('Time (ms)')
    ax.set_title('Convergence Time by Algorithm & Topology')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(fontsize=8)

    # 2. Iterations
    ax = axes[0, 1]
    for alg in plot_df['Algorithm'].unique():
        alg_data = plot_df[plot_df['Algorithm'] == alg]
        ax.bar([f"{row['Topology']}\n{alg}" for _, row in alg_data.iterrows()],
               alg_data['Iterations'], label=alg, alpha=0.7)
    ax.set_ylabel('Iterations')
    ax.set_title('Iterations to Converge')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(fontsize=8)

    # 3. Messages
    ax = axes[1, 0]
    for alg in plot_df['Algorithm'].unique():
        alg_data = plot_df[plot_df['Algorithm'] == alg]
        ax.bar([f"{row['Topology']}\n{alg}" for _, row in alg_data.iterrows()],
               alg_data['Messages'], label=alg, alpha=0.7)
    ax.set_ylabel('Messages')
    ax.set_title('Routing Messages Exchanged')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(fontsize=8)

    # 4. Path Cost / Hop Count
    ax = axes[1, 1]
    for alg in plot_df['Algorithm'].unique():
        alg_data = plot_df[plot_df['Algorithm'] == alg]
        # Filter numeric values
        numeric_data = alg_data[pd.to_numeric(alg_data['Avg Path Cost'], errors='coerce').notna()]
        if not numeric_data.empty:
            ax.bar([f"{row['Topology']}\n{alg}" for _, row in numeric_data.iterrows()],
                   pd.to_numeric(numeric_data['Avg Path Cost']), label=alg, alpha=0.7)
    ax.set_ylabel('Avg Path Cost / Hops')
    ax.set_title('Average Path Metric')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(fontsize=8)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    # Summary statistics
    st.divider()
    st.subheader(" Algorithm Summary Statistics")

    summary = generate_metrics_summary(collector)

    summary_data = []
    for alg, stats in summary.items():
        summary_data.append({
            'Algorithm': alg,
            'Avg Convergence Time (ms)': f"{stats['avg_convergence_time_ms']:.2f}",
            'Avg Iterations': f"{stats['avg_iterations']:.1f}",
            'Avg Messages': f"{stats['avg_messages']:.0f}",
            'Correctness Rate': f"{stats['correctness_rate']:.1%}",
            'Scenarios Tested': stats['run_count']
        })

    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # Strengths/Weaknesses table
    st.divider()
    st.subheader(" Algorithm Characteristics")

    characteristics = pd.DataFrame([
        {
            'Algorithm': 'Link-State (Dijkstra)',
            'Type': 'Link-State',
            'Metric': 'Configurable Cost',
            'Knowledge': 'Full Topology',
            'Convergence': 'Fast (Single Computation)',
            'Scalability': 'O(E log V) per router',
            'Loop-Free': 'Yes (by design)',
            'Memory': 'High (Full Topology DB)',
            'Best For': 'Enterprise, ISP Backbones'
        },
        {
            'Algorithm': 'Distance-Vector (Bellman-Ford)',
            'Type': 'Distance-Vector',
            'Metric': 'Configurable Cost',
            'Knowledge': 'Neighbor Vectors Only',
            'Convergence': 'Slower (Iterative)',
            'Scalability': 'O(V*E) worst case',
            'Loop-Free': 'No (Count-to-Infinity)',
            'Memory': 'Low (Distance Vectors)',
            'Best For': 'Small Networks, Simple Deployments'
        },
        {
            'Algorithm': 'RIP',
            'Type': 'Distance-Vector',
            'Metric': 'Hop Count (Max 15)',
            'Knowledge': 'Neighbor Vectors Only',
            'Convergence': 'Slow (Periodic Updates)',
            'Scalability': 'Limited (15 Hop Max)',
            'Loop-Free': 'With Split Horizon',
            'Memory': 'Very Low',
            'Best For': 'Small Homogeneous Networks'
        },
        {
            'Algorithm': 'OSPF',
            'Type': 'Link-State',
            'Metric': 'Cost (Bandwidth-based)',
            'Knowledge': 'Full Topology (per Area)',
            'Convergence': 'Fast (Triggered Updates)',
            'Scalability': 'Hierarchical (Areas)',
            'Loop-Free': 'Yes (by design)',
            'Memory': 'Medium (Per Area)',
            'Best For': 'Large Enterprise, ISP'
        }
    ])

    st.dataframe(characteristics, use_container_width=True)


def render_convergence_analysis():
    """Render detailed convergence analysis."""
    st.header(" Convergence Analysis")

    if 'topology' not in st.session_state or not st.session_state.topology.routers:
        st.warning(" No topology loaded.")
        return

    topo = st.session_state.topology

    from simulation.convergence import ConvergenceAnalyzer

    analyzer = ConvergenceAnalyzer(topo)

    if st.button("Analyze Convergence"):
        with st.spinner("Analyzing..."):
            metrics = analyzer.compare_algorithms()
        st.session_state.convergence_metrics = metrics
        st.success(" Analysis complete!")

    if 'convergence_metrics' in st.session_state:
        metrics = st.session_state.convergence_metrics

        # Display as table
        data = []
        for m in metrics:
            data.append({
                'Algorithm': m.algorithm,
                'Convergence Time (ms)': f"{m.convergence_time*1000:.2f}",
                'Iterations': m.iterations,
                'Messages': m.messages_exchanged,
                'Routes Correct': "✓" if m.final_routes_correct else "✗",
                'Route Changes': m.route_changes,
                'Max Distance Change': f"{m.max_distance_change:.1f}"
            })

        st.dataframe(pd.DataFrame(data), use_container_width=True)

        # Convergence plot for a specific route
        st.subheader(" Distance Convergence Plot")

        routers = list(topo.routers.keys())
        if len(routers) >= 2:
            col1, col2 = st.columns(2)
            with col1:
                src = st.selectbox("Source", routers, format_func=lambda x: f"{x} ({topo.routers[x].name})")
            with col2:
                dst = st.selectbox("Destination", routers, format_func=lambda x: f"{x} ({topo.routers[x].name})")

            if src != dst:
                # Run DV with history to get convergence data
                from algorithms.distance_vector import run_distance_vector, UpdateStrategy
                dv_result = run_distance_vector(topo, UpdateStrategy.SYNCHRONOUS, record_history=True)

                fig, ax = plt.subplots(figsize=(10, 5))
                iterations = []
                distances = []

                for rec in dv_result.iterations:
                    table = rec.tables.get(src)
                    if table:
                        entry = table.get_entry(dst)
                        iterations.append(rec.iteration)
                        dist = entry.distance
                        distances.append(dist if dist != float('inf') else None)

                valid = [(i, d) for i, d in zip(iterations, distances) if d is not None]
                if valid:
                    iters, dists = zip(*valid)
                    ax.plot(iters, dists, 'b-o', markersize=4)

                ax.set_xlabel('Iteration')
                ax.set_ylabel('Distance')
                ax.set_title(f'DV Convergence: {src} → {dst}')
                ax.grid(True, alpha=0.3)

                st.pyplot(fig)
                plt.close(fig)