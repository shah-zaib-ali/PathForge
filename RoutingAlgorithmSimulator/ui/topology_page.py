"""
Streamlit UI - Topology Builder Page
"""

import json

import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd
from network.topology import NetworkTopology, create_predefined_scenario, create_random_topology, Router, Link
from network.scenarios import SCENARIOS, list_scenarios, load_scenario


def render_topology_page():
    """Render the network topology builder page."""
    st.header(" Network Topology Builder")

    # Initialize session state for topology
    if 'topology' not in st.session_state:
        st.session_state.topology = NetworkTopology()
    if 'topology_name' not in st.session_state:
        st.session_state.topology_name = "Custom"

    topo = st.session_state.topology

    # Export/Import
    st.write("**Save/Load Topology**")
    json_str = json.dumps(topo.to_dict(), indent=2)
    st.download_button(
        "Export to JSON",
        json_str,
        file_name=f"topology_{st.session_state.topology_name}.json",
        mime="application/json"
    )

    uploaded = st.file_uploader("Import Topology", type=['json'])
    if uploaded is not None:
        # Import each uploaded file only once, otherwise every rerun
        # would overwrite routers/links added after the import.
        file_key = f"{uploaded.name}-{uploaded.size}"
        if st.session_state.get('last_import') != file_key:
            try:
                data = json.load(uploaded)
                st.session_state.topology = NetworkTopology.from_dict(data)
                st.session_state.topology_name = "Imported"
                st.session_state.last_import = file_key
                st.rerun()
            except Exception as e:
                st.error(f"Could not import topology: {e}")
    else:
        # Allow re-importing the same file after the uploader is cleared
        st.session_state.pop('last_import', None)

    # Main area - two columns
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Network Visualization")

        # Draw network
        fig = draw_topology(topo)
        st.pyplot(fig)
        plt.close(fig)

        # Network stats
        st.write(f"**Routers:** {len(topo.routers)} | **Links:** {len(topo.get_active_links())} | **Connected:** {'Yes' if topo.is_connected() else 'No'}")

    with col_right:
        st.subheader("Router Management")

        # Add router
        with st.expander(" Add Router", expanded=True):
            new_name = st.text_input("Router Name", placeholder="e.g., R4")
            if st.button("Add Router"):
                if new_name:
                    if any(r.name == new_name for r in topo.routers.values()):
                        st.error(f"Router '{new_name}' already exists!")
                    else:
                        topo.add_router(new_name)
                        st.success(f"Added router {new_name}")
                        st.rerun()
                else:
                    st.error("Please enter a router name")

        # Remove router
        if topo.routers:
            with st.expander(" Remove Router"):
                router_to_remove = st.selectbox(
                    "Select Router",
                    options=list(topo.routers.keys()),
                    format_func=lambda x: f"{x} ({topo.routers[x].name})"
                )
                if st.button("Remove Router"):
                    topo.remove_router(router_to_remove)
                    st.success(f"Removed router {router_to_remove}")
                    st.rerun()

    st.divider()

    # Link management in a container like Router Management
    with st.container(border=True):
        st.subheader("Link Management")

        if len(topo.routers) >= 2:
            # Add link
            with st.expander(" Add Link", expanded=True):
                router_ids = list(topo.routers.keys())
                col1, col2 = st.columns(2)
                with col1:
                    src = st.selectbox("Source", router_ids, format_func=lambda x: f"{x} ({topo.routers[x].name})", key="link_src")
                with col2:
                    tgt = st.selectbox("Target", router_ids, format_func=lambda x: f"{x} ({topo.routers[x].name})", key="link_tgt")

                cost = st.number_input("Cost", min_value=0.1, max_value=100.0, value=1.0, step=0.1)

                if st.button("Add Link"):
                    if src == tgt:
                        st.error("Cannot create self-loop")
                    else:
                        try:
                            topo.add_link(src, tgt, cost)
                            st.success(f"Added link {src}--{tgt} (cost={cost})")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

            # Build the list of links once (includes failed links)
            all_links = topo.get_all_links()
            link_options = {
                f"{l.source}--{l.target} (cost={l.cost}{', failed' if l.is_failed else ''})": l
                for l in all_links
            }

            # Modify links
            if link_options:
                with st.expander(" Modify Links"):
                    selected_link_str = st.selectbox("Select Link", list(link_options.keys()), key="modify_link")
                    selected_link = link_options[selected_link_str]

                    col1, col2 = st.columns(2)
                    with col1:
                        new_cost = st.number_input("New Cost", min_value=0.1, max_value=100.0, value=float(selected_link.cost), step=0.1)
                    with col2:
                        failed = st.checkbox("Mark as Failed", value=selected_link.is_failed)

                    if st.button("Update Link"):
                        topo.update_link_cost(selected_link.source, selected_link.target, new_cost)
                        if failed != selected_link.is_failed:
                            topo.set_link_failed(selected_link.source, selected_link.target, failed)
                        st.success("Link updated")
                        st.rerun()

                # Remove link
                with st.expander(" Remove Link"):
                    link_to_remove = st.selectbox("Select Link to Remove", list(link_options.keys()), key="remove_link")
                    if st.button("Remove Link"):
                        link = link_options[link_to_remove]
                        topo.remove_link(link.id)
                        st.success("Link removed")
                        st.rerun()
        else:
            st.info("Add at least 2 routers to create links")

    # Routing tables preview
    if topo.routers:
        st.divider()
        st.subheader("Current Topology Summary")

        # Router table
        router_data = []
        for rid, router in topo.routers.items():
            neighbors = [f"{n} (cost={c})" for n, c in topo.get_neighbors(rid)]
            router_data.append({
                'ID': rid,
                'Name': router.name,
                'Neighbors': ', '.join(neighbors) if neighbors else 'None'
            })
        st.dataframe(pd.DataFrame(router_data), use_container_width=True)

        # Link table
        link_data = []
        for link in topo.get_all_links():
            status = "Failed" if link.is_failed else "Active"
            link_data.append({
                'Source': link.source,
                'Target': link.target,
                'Cost': link.cost,
                'Status': status
            })
        if link_data:
            st.dataframe(pd.DataFrame(link_data), use_container_width=True)


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------

def _compute_positions(topo: NetworkTopology) -> dict:
    """
    Return {router_id: (x, y)} normalised to the range [-1, 1].

    Uses topo.get_layout() when it returns a complete, non-overlapping layout;
    otherwise falls back to a fresh networkx layout so newly added routers are
    never stacked on top of each other or missing.
    """
    ids = list(topo.routers.keys())
    pos = None

    try:
        raw = topo.get_layout()
        if raw and all(r in raw for r in ids):
            pts = {r: (float(raw[r][0]), float(raw[r][1])) for r in ids}
            unique = {(round(x, 3), round(y, 3)) for x, y in pts.values()}
            if len(unique) == len(ids):
                pos = pts
    except Exception:
        pos = None

    if pos is None:
        g = nx.Graph()
        g.add_nodes_from(ids)
        for link in topo.get_all_links():
            if link.source in topo.routers and link.target in topo.routers:
                g.add_edge(link.source, link.target)

        if g.number_of_edges() == 0 or len(ids) < 3:
            raw = nx.circular_layout(g)
        else:
            raw = nx.spring_layout(g, seed=42)
        pos = {r: (float(raw[r][0]), float(raw[r][1])) for r in ids}

    # Normalise to [-1, 1] while keeping the aspect ratio
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    scale = max(max(xs) - min(xs), max(ys) - min(ys)) / 2
    if scale == 0:
        scale = 1.0
    return {r: ((x - cx) / scale, (y - cy) / scale) for r, (x, y) in pos.items()}


def _draw_router_icon(ax, x, y, name):
    """Draw a router-shaped icon (body, antennas, LEDs) centred at (x, y)."""
    w, h = 0.38, 0.19

    # Antennas (behind the body)
    for dx, tip_dx in ((-0.11, -0.05), (0.11, 0.05)):
        base = (x + dx, y + h / 2)
        tip = (x + dx + tip_dx, y + h / 2 + 0.13)
        ax.plot([base[0], tip[0]], [base[1], tip[1]],
                color='#1f3b57', linewidth=3, solid_capstyle='round', zorder=4)
        ax.add_patch(plt.Circle(tip, 0.016, fc='#1f3b57', ec='#1f3b57', zorder=4))

    # Body
    body = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.04",
        fc='#cfe8ff', ec='#1f3b57', linewidth=2.5, zorder=5
    )
    ax.add_patch(body)

    # LEDs along the bottom edge of the front panel
    for i, led_color in enumerate(('#2ecc71', '#2ecc71', '#f1c40f')):
        lx = x - 0.10 + i * 0.05
        ax.add_patch(plt.Circle((lx, y - 0.06), 0.012, fc=led_color,
                                ec='#1f3b57', linewidth=0.8, zorder=6))

    # Router name
    ax.text(x, y + 0.02, name, ha='center', va='center',
            fontsize=10, fontweight='bold', color='#1f3b57', zorder=7)


def draw_topology(topo: NetworkTopology) -> plt.Figure:
    """Draw network topology using matplotlib."""
    fig, ax = plt.subplots(figsize=(10, 7))

    if not topo.routers:
        ax.text(0.5, 0.5, "No routers in topology", ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig

    # Get a safe, normalised layout
    pos = _compute_positions(topo)

    # Draw edges
    for link in topo.get_all_links():
        if link.source not in pos or link.target not in pos:
            continue
        src_pos = pos[link.source]
        tgt_pos = pos[link.target]

        color = 'red' if link.is_failed else 'gray'
        style = '--' if link.is_failed else '-'
        width = 1.5 if link.is_failed else 2.5

        ax.plot([src_pos[0], tgt_pos[0]], [src_pos[1], tgt_pos[1]],
                color=color, linestyle=style, linewidth=width, zorder=1)

        # Label with cost
        mid_x = (src_pos[0] + tgt_pos[0]) / 2
        mid_y = (src_pos[1] + tgt_pos[1]) / 2
        ax.text(mid_x, mid_y, f"{link.cost}", fontsize=9, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.9),
                zorder=3)

    # Draw routers
    for rid, router in topo.routers.items():
        x, y = pos[rid]
        _draw_router_icon(ax, x, y, router.name)

    # Set limits explicitly (add_patch does not autoscale, and with no links
    # nothing else does either, which made new routers appear clipped/missing)
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.3, 1.4)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"Network Topology: {st.session_state.get('topology_name', 'Custom')}", fontsize=14, pad=20)

    return fig