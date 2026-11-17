"""
Streamlit UI - Theory & Educational Page
"""

import streamlit as st
import pandas as pd


def render_theory_page():
    """Render the educational theory page."""
    st.header(" Routing Algorithm Theory & Concepts")

    # Table of contents
    st.sidebar.markdown("### Topics")
    topics = [
        "What is Routing?",
        "Control Plane vs Data Plane",
        "Convergence"
    ]

    selected_topic = st.sidebar.radio("Select Topic", topics)

    # Render selected topic
    if selected_topic == "What is Routing?":
        render_what_is_routing()
    elif selected_topic == "Control Plane vs Data Plane":
        render_control_vs_data_plane()
    elif selected_topic == "Convergence":
        render_convergence()


def render_what_is_routing():
    st.subheader(" What is Routing?")

    st.markdown("""
**Routing** is the process of selecting paths in a network along which to send data packets.

### Key Concepts

- **Router:** A device that forwards packets between networks
- **Routing Table:** A data structure storing best paths to destinations
- **Metric:** A value used to compare path quality (cost, hops, bandwidth, delay)
- **Convergence:** The process of all routers agreeing on the network topology

### Why Routing is Needed

1. **Interconnect Networks:** Connect LANs, WANs, and the Internet
2. **Path Selection:** Choose the best path among multiple options
3. **Fault Tolerance:** Reroute around failures automatically
4. **Scalability:** Handle networks with thousands of routers

### Routing vs Forwarding

| Aspect | Routing (Control Plane) | Forwarding (Data Plane) |
|--------|------------------------|------------------------|
| **Function** | Build/maintain routing tables | Move packets toward destination |
| **Timescale** | Seconds to minutes | Nanoseconds to microseconds |
| **Decision** | Complex algorithms | Simple table lookup |
| **Protocols** | OSPF, RIP, BGP, IS-IS | IP, MPLS, Ethernet |
""")


def render_control_vs_data_plane():
    st.subheader(" Control Plane vs Data Plane")

    st.markdown("""
### Control Plane (Routing)

- **Runs routing protocols** (OSPF, RIP, BGP)
- **Builds routing tables** (RIB - Routing Information Base)
- **Exchanges routing information** with neighbors
- **Computes best paths** using algorithms
- **Reacts to topology changes**

### Data Plane (Forwarding)

- **Forwards packets** based on FIB (Forwarding Information Base)
- **Performs lookups** at line rate
- **Applies QoS, ACLs, NAT**
- **Handles encapsulation/decapsulation**
- **Implemented in hardware** (ASICs, NPUs) for speed

### Separation Benefits

1. **Performance:** Data plane optimized for speed
2. **Reliability:** Control plane failure doesn't stop forwarding immediately
3. **Scalability:** Different scaling requirements
3. **Programmability:** SDN separates control plane to centralized controller
""")


def render_ls_vs_dv():
    st.subheader(" Link-State vs Distance-Vector")

    st.markdown("""
### Link-State Routing

**How it works:**
1. Each router discovers its neighbors and link costs
2. Routers flood **Link-State Advertisements (LSAs)** to all routers
3. Every router builds an **identical topology database** (LSDB)
4. Each router independently runs **Dijkstra's algorithm** on the LSDB
5. Results in a **Shortest Path Tree** rooted at that router

**Characteristics:**
- Fast convergence
- Loop-free by design
- Each router has complete topology view
- Higher memory/CPU requirements
- More complex implementation
- Flooding overhead in large networks

**Protocols:** OSPF, IS-IS

### Distance-Vector Routing

**How it works:**
1. Each router knows only **directly connected links**
2. Routers periodically send **distance vectors** to neighbors
3. Neighbors update their tables using **Bellman-Ford equation**:
    ```
D_x(y) = min_v [ c(x,v) + D_v(y) ]
```
4. Process repeats until **convergence**

**Characteristics:**
- Simple implementation
- Low memory requirements
- Only neighbor communication needed
- Slow convergence
- Count-to-infinity problem
- Routing loops possible
- No global topology view

**Protocols:** RIP, IGRP (legacy)
""")


def render_dijkstra():
    st.subheader(" Dijkstra's Shortest Path Algorithm")

    st.markdown("""
### Algorithm Overview

Dijkstra's algorithm finds shortest paths from a **single source** to all destinations
in a graph with **non-negative edge weights**.

### Step-by-Step Process

1. **Initialize:**
- Distance to source = 0
- Distance to all others = ∞
- All nodes unvisited
- Priority queue with (0, source)

2. **Main Loop:**
- Extract node with minimum distance from queue
- Mark as visited (finalized)
- For each neighbor:
    - Calculate new distance = current distance + edge cost
- If new distance < recorded distance:
    - Update distance and predecessor
- Add/update in priority queue

3. **Terminate:** When queue is empty or all nodes visited

### Pseudocode
```
function Dijkstra(Graph, source):
    dist[source] = 0
for each vertex v ≠ source:
    dist[v] = ∞
prev[v] = undefined

Q = priority queue with all vertices

while Q not empty:
    u = vertex in Q with min dist[u]
remove u from Q

for each neighbor v of u:
    alt = dist[u] + weight(u, v)
if alt < dist[v]:
    dist[v] = alt
prev[v] = u
update Q

return dist, prev
```

### Complexity

| Implementation | Time Complexity |
|----------------|-----------------|
| Array | O(V²) |
| Binary Heap | O((V + E) log V) |
| Fibonacci Heap | O(E + V log V) |

### Example Walkthrough

**Network:**
```
A --(4)-- B --(2)-- D
\\ |
(3) (1)
\\ |
C --(5)
```

**From A:**
1. Start: dist[A]=0, others=∞
2. Visit A: update B=4, C=3
3. Visit C: update D=8 (via C), B=4 (no change)
4. Visit B: update D=6 (via B, better than 8)
5. Visit D: done

**Result:** A→B=4, A→C=3, A→D=6 (via B)
""")


def render_bellman_ford():
    st.subheader(" Bellman-Ford / Distance Vector Algorithm")

    st.markdown("""
### Bellman-Ford Equation

The core of Distance Vector routing:
    ```
D_x(y) = min over all neighbors v of [ c(x,v) + D_v(y) ]
```

Where:
    - `D_x(y)` = Distance from router x to destination y
- `c(x,v)` = Cost of direct link from x to neighbor v
- `D_v(y)` = Distance from neighbor v to destination y (from v's vector)

### Iterative Process

1. **Initialization:** Each router knows only direct link costs
2. **Exchange:** Routers send distance vectors to neighbors
3. **Update:** Each router applies Bellman-Ford equation
4. **Repeat:** Until no changes (convergence)

### Example: 3-Node Network

```
R1 --(1)-- R2 --(1)-- R3
```

**Initial State:**
| Router | To R1 | To R2 | To R3 |
|--------|-------|-------|-------|
| R1 | 0 | 1 | ∞ |
| R2 | 1 | 0 | 1 |
| R3 | ∞ | 1 | 0 |

**After Iteration 1:**
- R1 learns from R2: R3 at distance 2
- R3 learns from R2: R1 at distance 2

**After Iteration 2:** Converged
| Router | To R1 | To R2 | To R3 |
|--------|-------|-------|-------|
| R1 | 0 | 1 | 2 |
| R2 | 1 | 0 | 1 |
| R3 | 2 | 1 | 0 |

### Synchronous vs Asynchronous Updates

- **Synchronous:** All routers update simultaneously each round
- **Asynchronous:** Routers update in random/arbitrary order

Both converge to same result, but timing differs.
""")


def render_ospf():
    st.subheader(" OSPF (Open Shortest Path First)")

    st.markdown("""
### Overview

OSPF is a **Link-State** Interior Gateway Protocol (IGP) widely used in enterprise and ISP networks.

### Key Features

**Hierarchical Design (Areas):**
- **Area 0 (Backbone):** Core transit area
- **Regular Areas:** Connect to backbone via ABRs
- **Stub/Totally Stub/NSSA:** Special area types for optimization

**Router Types:**
- **Internal Router:** All interfaces in one area
- **Area Border Router (ABR):** Connects multiple areas
- **Backbone Router:** Has interface in Area 0
- **ASBR:** Redistributes external routes

**Link-State Advertisements (LSAs):**
- **Type 1 (Router LSA):** Links within area
- **Type 2 (Network LSA):** Multi-access networks (DR/BDR)
- **Type 3 (Summary LSA):** Inter-area routes (ABR)
- **Type 4 (ASBR Summary):** Path to ASBR
- **Type 5 (External LSA):** External routes (ASBR)
- **Type 7 (NSSA External):** External in NSSA

### OSPF Operation

1. **Hello Protocol:** Discover neighbors, elect DR/BDR
2. **Database Exchange:** Synchronize LSDBs
3. **Link-State Flooding:** Distribute LSAs
4. **SPF Calculation:** Run Dijkstra per area
5. **Routing Table:** Install best paths

### Metrics

- **Cost = Reference Bandwidth / Interface Bandwidth**
- Default Reference = 100 Mbps (configurable)
- Example: 1 Gbps = cost 1, 100 Mbps = cost 1, 10 Mbps = cost 10

### Advantages
- Fast convergence (seconds)
- Loop-free
- Hierarchical scaling
- VLSM/CIDR support
- Authentication
- Equal-cost multipath (ECMP)
""")


def render_rip():
    st.subheader(" RIP (Routing Information Protocol)")

    st.markdown("""
### Overview

RIP is a **Distance-Vector** protocol using **hop count** as metric.
One of the oldest routing protocols (RIPv1: 1988, RIPv2: 1993).

### Key Characteristics

**Metric:** Hop Count
- Each router hop = 1
- **Maximum = 15 hops**
- **16 = Unreachable (Infinity)**

**Timers (RIPv2):**
- **Update Timer:** 30 seconds (periodic full table)
- **Invalid Timer:** 180 seconds (mark route invalid)
- **Hold-down Timer:** 180 seconds (suppress updates)
- **Flush Timer:** 240 seconds (remove from table)

**RIPv1 vs RIPv2:**
| Feature | RIPv1 | RIPv2 |
|---------|-------|-------|
| Subnet Mask | No (classful) | Yes (classless) |
| Authentication | No | Yes (simple/MD5) |
| Multicast | No (broadcast) | Yes (224.0.0.9) |
| VLSM | No | Yes |

### Loop Prevention

1. **Split Horizon:** Don't advertise back to source
2. **Poisoned Reverse:** Advertise with metric 16
3. **Triggered Updates:** Immediate update on change
4. **Hold-down:** Wait before accepting new route

### Limitations

- 15-hop limit restricts network diameter
- Slow convergence (minutes)
- No concept of bandwidth/cost
- Periodic full updates waste bandwidth
- Count-to-infinity possible

### When to Use

- Small, simple networks
- Homogeneous bandwidth links
- Legacy equipment support
- Learning/educational purposes
""")


def render_convergence():
    st.subheader("⏱ Routing Convergence")

    st.markdown("""
### What is Convergence?

**Convergence** is the process by which all routers in a network
reach a consistent view of the topology after a change.

### Convergence Steps

1. **Detection:** Link/neighbor failure detected
2. **Propagation:** Update messages flood through network
3. **Computation:** Each router recalculates routes
4. **Installation:** New routes installed in FIB

### Convergence Time Factors

| Factor | Link-State | Distance-Vector |
|--------|------------|-----------------|
| Detection | Fast (Hello) | Fast (Hello) |
| Propagation | Flooding (parallel) | Hop-by-hop (serial) |
| Computation | Dijkstra (per router) | Bellman-Ford (iterative) |
| Total | **Seconds** | **Minutes** |

### Convergence Metrics

- **Detection Time:** Time to detect failure
- **Propagation Time:** Time for updates to reach all routers
- **Computation Time:** Time to run SPF/DV algorithm
- **Total Convergence Time:** Sum of above

### Fast Convergence Techniques

- **Bidirectional Forwarding Detection (BFD):** Sub-second detection
- **Incremental SPF:** Only recompute affected parts
- **Prefix Prioritization:** Critical routes first
- **Loop-Free Alternates (LFA):** Pre-computed backup paths
""")


def render_routing_loops():
    st.subheader(" Routing Loops")

    st.markdown("""
### What is a Routing Loop?

A **routing loop** occurs when packets cycle between routers
without reaching their destination.

### Example Loop

```
R1 thinks R3 is via R2
R2 thinks R3 is via R1

Packet: R1 → R2 → R1 → R2 → ... (TTL expires)
```

### Causes

1. **Slow Convergence:** Inconsistent tables during transition
2. **Incorrect Metrics:** Asymmetric link costs
3. **Redistribution:** Routes fed between protocols incorrectly
4. **Count-to-Infinity:** DV-specific (see next section)

### Effects

- **Packet Loss:** TTL expires
- **Bandwidth Waste:** Packets circulate
- **CPU Load:** Processing looped packets
- **Network Meltdown:** Congestion collapse

### Prevention

- **Link-State:** Inherently loop-free (global view)
- **Distance-Vector:** Split horizon, poisoned reverse, hold-down
- **Path Vector (BGP):** AS-PATH loop detection
- **TTL/Hop Limit:** Ultimate safety net
""")


def render_count_to_infinity_theory():
    st.subheader(" Count-to-Infinity Problem")

    st.markdown("""
### The Problem

**Count-to-Infinity** is a specific failure mode in Distance Vector routing
where routers slowly increment the metric for an unreachable destination.

### Classic Scenario

```
R1 --(1)-- R2 --(1)-- R3
```

**Initial:** R1→R3 = 2 (via R2), R2→R3 = 1 (direct)

**Failure:** R2-R3 link goes down

**Step-by-Step:**

| Step | Event | R1→R3 | R2→R3 |
|------|-------|-------|-------|
| 0 | Initial | 2 (via R2) | 1 (direct) |
| 1 | R2-R3 fails | 2 (via R2) | ∞ (lost direct) |
| 2 | R2 hears R1: "R3 at 2" | 2 (via R2) | 3 (via R1) |
| 3 | R1 hears R2: "R3 at 3" | 4 (via R2) | 3 (via R1) |
| 4 | R2 hears R1: "R3 at 4" | 4 (via R2) | 5 (via R1) |
| ... | Continues... | Increases | Increases |
| N | Reaches 16 | 16 (∞) | 16 (∞) |

### Why It Happens

- R1 believes R2 has a path to R3
- R2 believes R1 has a path to R3
- **Neither realizes the path goes through the other!**
- This is a **2-node routing loop**

### Mathematical View

Distance increases by 2 each full cycle (R1→R2→R1):
    - Even iterations: R1 distance = 2k, R2 distance = 2k-1
- Odd iterations: R1 distance = 2k, R2 distance = 2k+1

### RIP Specifics

- Infinity = 16
- Maximum usable hops = 15
- Takes ~8 cycles to reach infinity in 3-node case
- With 4+ nodes, takes longer

### When It Doesn't Happen

- Link-State protocols (global view prevents it)
- DV with Split Horizon (don't advertise back to source)
- DV with Poisoned Reverse (advertise infinity back)
- Topology where failed destination has no alternate path
""")


def render_split_horizon():
    st.subheader(" Split Horizon & Poisoned Reverse")

    st.markdown("""
### Split Horizon

**Rule:** Never advertise a route back to the neighbor you learned it from.

**Logic:** If I learned about destination D from neighbor N,
then N already knows about D (at least as good as I do).
Telling N "I can reach D" creates a loop.

### Example: 3-Node with Split Horizon

```
R1 --(1)-- R2 --(1)-- R3
```

**After R2-R3 fails:**

- R2 loses direct route to R3
- R1 would normally tell R2: "I can reach R3 in 2 hops"
- **With Split Horizon:** R1 learned R3 from R2, so R1 **doesn't** tell R2
- R2 never gets false route → **No count-to-infinity!**

### Poisoned Reverse

**Rule:** Advertise the route back with metric = INFINITY.

**Logic:** Actively tell neighbor "my route to D is broken" instead of staying silent.

**Example:**
- R1 learned R3 from R2
- R1 sends to R2: "R3 at metric 16 (unreachable)"
- R2 immediately knows path via R1 is invalid
- **Faster convergence than simple split horizon**

### Comparison

| Technique | Loop Prevention | Convergence Speed | Bandwidth |
|-----------|-----------------|-------------------|-----------|
| None | ❌ | Slow | Low |
| Split Horizon | ✓ (2-node) | Medium | Low |
| Poisoned Reverse | ✓ (2-node) | Fast | Medium |
| Hold-down | ✓ (general) | Slow | Low |

### Limitations

- **Split Horizon only prevents 2-node loops**
- **3+ node loops still possible** (e.g., R1→R2→R3→R1)
- **Poisoned Reverse helps but not perfect**
- **Modern networks use Link-State (OSPF/IS-IS) instead**
""")


def render_comparison_table():
    st.subheader(" Algorithm Comparison Table")

    comparison = pd.DataFrame([
        {
            'Aspect': 'Algorithm Type',
            'Link-State (OSPF/IS-IS)': 'Link-State',
            'Distance-Vector (RIP)': 'Distance-Vector',
            'Path Vector (BGP)': 'Path Vector'
        },
        {
            'Aspect': 'Metric',
            'Link-State (OSPF/IS-IS)': 'Cost (bandwidth, delay, configurable)',
            'Distance-Vector (RIP)': 'Hop Count (max 15)',
            'Path Vector (BGP)': 'AS-PATH length + attributes'
        },
        {
            'Aspect': 'Topology Knowledge',
            'Link-State (OSPF/IS-IS)': 'Full (entire area)',
            'Distance-Vector (RIP)': 'Neighbors only',
            'Path Vector (BGP)': 'AS-PATH to destination'
        },
        {
            'Aspect': 'Update Mechanism',
            'Link-State (OSPF/IS-IS)': 'Flooding (triggered)',
            'Distance-Vector (RIP)': 'Periodic + triggered',
            'Path Vector (BGP)': 'Incremental (triggered)'
        },
        {
            'Aspect': 'Convergence Speed',
            'Link-State (OSPF/IS-IS)': 'Fast (seconds)',
            'Distance-Vector (RIP)': 'Slow (minutes)',
            'Path Vector (BGP)': 'Variable (policy-dependent)'
        },
        {
            'Aspect': 'Loop Prevention',
            'Link-State (OSPF/IS-IS)': 'Inherent (global view)',
            'Distance-Vector (RIP)': 'Split horizon, poisoned reverse',
            'Path Vector (BGP)': 'AS-PATH loop detection'
        },
        {
            'Aspect': 'Scalability',
            'Link-State (OSPF/IS-IS)': 'Hierarchical (areas)',
            'Distance-Vector (RIP)': 'Limited (15 hops)',
            'Path Vector (BGP)': 'Internet-scale (60k+ prefixes)'
        },
        {
            'Aspect': 'Memory/CPU',
            'Link-State (OSPF/IS-IS)': 'Higher (LSDB + SPF)',
            'Distance-Vector (RIP)': 'Low (vectors only)',
            'Path Vector (BGP)': 'High (full routing table)'
        },
        {
            'Aspect': 'Configuration Complexity',
            'Link-State (OSPF/IS-IS)': 'Medium-High',
            'Distance-Vector (RIP)': 'Low',
            'Path Vector (BGP)': 'High (policy-based)'
        },
        {
            'Aspect': 'Typical Use Case',
            'Link-State (OSPF/IS-IS)': 'Enterprise, ISP backbone',
            'Distance-Vector (RIP)': 'Small networks, lab',
            'Path Vector (BGP)': 'Inter-domain (Internet)'
        }
    ])

    st.dataframe(comparison, use_container_width=True)

    st.markdown("""
### Key Takeaways

1. **Link-State** excels in large, complex networks needing fast convergence
2. **Distance-Vector** suits small, simple networks with limited resources
3. **Path Vector (BGP)** is the only choice for inter-domain routing
4. **RIP is largely obsolete** for production but valuable for education
5. **OSPF/IS-IS** are the standard for modern enterprise/ISP IGP
""")


def render_worked_examples():
    st.subheader(" Worked Examples")

    tab1, tab2, tab3 = st.tabs(["Dijkstra Example", "DV Example", "RIP vs Cost"])

    with tab1:
        st.markdown("""
### Dijkstra Example: 4-Node Network

```
A --(4)-- B --(2)-- D
\\ |
(3) (1)
\\ |
C --(5)
```

**From A:**

| Step | Visited | Queue (dist, node) | Distances | Notes |
|------|---------|-------------------|-----------|-------|
| 0 | {} | (0,A) | A=0, B=∞, C=∞, D=∞ | Init |
| 1 | {A} | (3,C), (4,B) | A=0, B=4, C=3, D=∞ | Visit A, relax B,C |
| 2 | {A,C} | (4,B), (8,D) | A=0, B=4, C=3, D=8 | Visit C, relax D |
| 3 | {A,C,B} | (6,D) | A=0, B=4, C=3, D=6 | Visit B, relax D (6<8) |
| 4 | {A,C,B,D} | - | A=0, B=4, C=3, D=6 | Visit D, done |

**Final Paths from A:**
- A→B: 4 (direct)
- A→C: 3 (direct)
- A→D: 6 (via B)
""")

    with tab2:
        st.markdown("""
### Distance Vector Example: 3-Node Line

```
R1 --(1)-- R2 --(1)-- R3
```

**Iteration 0 (Initial):**
| Router | R1 | R2 | R3 |
|--------|---|---|---|
| R1 | 0 | 1 | ∞ |
| R2 | 1 | 0 | 1 |
| R3 | ∞ | 1 | 0 |

**Iteration 1:**
- R1 receives from R2: R3=1 → R1 updates R3=2 (via R2)
- R3 receives from R2: R1=1 → R3 updates R1=2 (via R2)

| Router | R1 | R2 | R3 |
|--------|---|---|---|
| R1 | 0 | 1 | 2 |
| R2 | 1 | 0 | 1 |
| R3 | 2 | 1 | 0 |

**Iteration 2:** No changes → **Converged!**
""")

    with tab3:
        st.markdown("""
### RIP (Hop Count) vs Link-State (Cost)

**Network:**
```
R1 --(10)-- R2 --(10)-- R4
\\ | /
(2) (1) (3)
\\ | /
R3 ------+
```
- Path 1: R1-R2-R4 = 2 hops, cost 20
- Path 2: R1-R3-R4 = 2 hops, cost 5
- Path 3: R1-R2-R3-R4 = 3 hops, cost 4

**RIP Decision:** Path 1 or 2 (both 2 hops) - prefers lower next-hop IP typically
**Link-State Decision:** Path 3 (cost 4) - lowest total cost despite 3 hops

**This shows:** Different metrics optimize for different things!
- Hop count = minimize router traversals
- Cost = minimize total "expense" (delay, bandwidth inverse, etc.)
""")


def render_theory_page_with_examples():
    render_theory_page()
    st.divider()
    render_worked_examples()