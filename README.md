# Routing Algorithm Simulator

**Link-State vs Distance-Vector, Validated Against OSPF**

A university-level Computer Networks project implementing an interactive simulator for routing algorithms with Streamlit web interface.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)
![NetworkX](https://img.shields.io/badge/NetworkX-3.1%2B-orange)
![License](https://img.shields.io/badge/License-MIT-green)

##  Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [User Guide](#user-guide)
- [Algorithm Explanations](#algorithm-explanations)
- [Sample Scenarios](#sample-scenarios)
- [Limitations](#limitations)
- [Future Enhancements](#future-enhancements)

##  Overview

This project implements a complete educational simulator for routing algorithms used in computer networks. It demonstrates:

1. **Link-State Routing** - Dijkstra's shortest path algorithm with step-by-step visualization
2. **Distance-Vector Routing** - Iterative Bellman-Ford updates (synchronous & asynchronous)
3. **RIP Simulation** - Hop-count metric with split horizon and poisoned reverse
4. **Count-to-Infinity Problem** - Reproducible demonstration with distance plots
5. **OSPF Validation** - Correctness verification against NetworkX reference
6. **Performance Comparison** - Metrics, charts, and algorithm characteristics
7. **Experimental Evaluation** - Repeated routing runs under 20, 100, and 200 ms RTT conditions, reporting means and sample standard deviations

##  Features

### Network Topology Builder
- Interactive graph editor with drag-and-drop style controls
- Add/remove routers and links with configurable costs
- Predefined scenarios (8 built-in topologies)
- Random topology generator
- Link failure simulation and recovery
- Import/export topology as JSON

### Link-State Routing (Dijkstra)
- From-scratch Dijkstra implementation (not NetworkX wrapper)
- Step-by-step algorithm visualization
- Tentative distances, predecessors, priority queue state
- Shortest path tree and routing tables
- Path highlighting on network diagram

### Distance-Vector Routing (Bellman-Ford)
- Synchronous and asynchronous update modes
- Per-iteration routing table display
- Route change tracking
- Convergence detection and visualization
- Distance evolution plots

### RIP Simulation
- Hop-count metric (max 15, infinity = 16)
- Split horizon and poisoned reverse options
- Periodic/triggered update behavior
- Comparison with cost-based routing

### Count-to-Infinity Demonstration
- Classic 3-node (R1-R2-R3) scenario
- 4-node line topology scenario
- Step-by-step distance tracking
- Distance vs iteration plots
- Educational explanation of the problem

### OSPF Validation
- Automated comparison against NetworkX shortest_path
- Per-router, per-destination validation
- Distance, next-hop, and path verification
- Detailed mismatch reporting
- CSV export of results

### Performance Comparison
- Multi-topology benchmarking
- Convergence time, iterations, messages
- Bar charts and summary statistics
- Algorithm characteristics table

### Experimental Evaluation
- Repeated synchronous Distance-Vector and RIP runs under 20, 100, and 200 ms RTT conditions
- Configurable run count (minimum 3) on a selected connected topology
- Mean and sample standard deviation for simulated convergence delay, execution time, iterations, messages, route metric, and correctness
- CSV downloads for summary and individual run measurements
- Simulated convergence delay assumes one RTT per routing update iteration; it is not real packet timing or packet-loss simulation

### Educational Content
- Theory explanations for all concepts
- Worked examples with calculations
- Algorithm comparison table
- Mitigation techniques for routing problems

##  Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.8+ | Core implementation |
| Web UI | Streamlit | Interactive web interface |
| Graphs | NetworkX | Topology representation, reference algorithms |
| Data | pandas | Routing tables, results, metrics |
| Plots | matplotlib | Network diagrams, convergence charts |
| Testing | unittest | Automated test suite |

##  Project Structure

```
RoutingAlgorithmSimulator/
├── app.py                      # Main Streamlit entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
├── algorithms/
│   ├── __init__.py
│   ├── link_state.py           # Dijkstra implementation
│   ├── distance_vector.py      # Bellman-Ford implementation
│   ├── rip.py                  # RIP simulation
│   └── ospf_validation.py      # NetworkX validation
├── network/
│   ├── __init__.py
│   ├── topology.py             # Topology management
│   └── scenarios.py            # Predefined scenarios
├── simulation/
│   ├── __init__.py
│   ├── convergence.py          # Convergence analysis
│   ├── count_to_infinity.py    # Count-to-infinity demo
│   └── metrics.py              # Performance metrics
├── ui/
│   ├── __init__.py
│   ├── topology_page.py        # Topology builder
│   ├── link_state_page.py      # Link-State routing
│   ├── distance_vector_page.py # Distance-Vector routing
│   ├── rip_page.py             # RIP simulation
│   ├── count_to_infinity_page.py # Count-to-infinity
│   ├── validation_page.py      # OSPF validation
│   ├── comparison_page.py      # Performance comparison
│   └── theory_page.py          # Educational content
└── tests/
    ├── __init__.py
    ├── test_link_state.py
    ├── test_distance_vector.py
    ├── test_rip.py
    ├── test_validation.py
    └── test_topology.py
```

##  Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Windows Setup (PowerShell)

```powershell
# 1. Clone or navigate to project directory
cd C:\Users\User\Desktop\RoutingAlgorithmSimulator

# 2. Create virtual environment (if not already created)
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\Activate.ps1

# 4. Verify activation (should show (.venv) prefix)
# 5. Install dependencies
pip install -r requirements.txt

# 6. Verify installation
python -c "import streamlit, networkx, pandas, matplotlib; print('All packages OK')"
```

### Alternative: Using Existing Environment

If you already have a virtual environment with the dependencies installed:

```powershell
# Activate existing environment
.venv\Scripts\Activate.ps1

# Verify packages are available
python -c "import streamlit, networkx, pandas, matplotlib; print('OK')"
```

##  Running the Application

```powershell
# From project root directory
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### First Run Checklist

1.  Virtual environment activated
2.  Dependencies installed (`pip install -r requirements.txt`)
3.  Run `streamlit run app.py`
4.  Browser opens to the simulator

##  Running Tests

```powershell
# Run all tests with verbose output
python -m unittest discover -s tests -v

# Run specific test module
python -m unittest tests.test_link_state -v
python -m unittest tests.test_distance_vector -v
python -m unittest tests.test_rip -v
python -m unittest tests.test_validation -v
python -m unittest tests.test_topology -v

# Run tests from Streamlit UI
# Navigate to "Testing & About" → "Run Tests"
```

### Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Link-State | 7 | Dijkstra, paths, failures, steps |
| Distance-Vector | 8 | Convergence, sync/async, loops |
| RIP | 6 | Hop limits, loop prevention, comparison |
| Validation | 5 | NetworkX comparison, changes |
| Topology | 8 | CRUD, scenarios, serialization |

##  User Guide

### 1. Network Topology Builder
- **Add Router**: Enter name, click "Add Router"
- **Add Link**: Select source/target, enter cost, click "Add Link"
- **Modify Link**: Select link, change cost or mark failed
- **Load Scenario**: Choose from sidebar dropdown
- **Generate Random**: Set router/link count, click "Generate Random"

### 2. Link-State Routing
- Select source router from dropdown
- Click "Compute Shortest Paths"
- View routing table and path visualization
- Use step slider to see Dijkstra iterations
- Click "Compute for All Routers" for full tables

### 3. Distance-Vector Routing
- Choose update strategy (synchronous/asynchronous)
- Set max iterations
- Click "Run Distance-Vector Simulation"
- Use iteration slider to see convergence
- Compare strategies with "Run Both Strategies"

### 4. RIP Simulation
- Enable/disable split horizon and poisoned reverse
- Click "Run RIP Simulation"
- View hop-count routing tables
- Compare modes with "Run All RIP Modes"
- Compare with Link-State using "Compare RIP vs Link-State"

### 5. Count-to-Infinity
- Select scenario (3-node or 4-node)
- Click "Run Count-to-Infinity Demo"
- View distance evolution table and plot
- Read educational explanation

### 6. OSPF Validation
- Choose "Validate All Routers" or single source
- Click "Run Validation"
- Review pass/fail results
- Download CSV report

### 7. Performance Comparison
- Select topologies to compare
- Click "Run Comparison"
- View charts and summary table

### 8. Experimental Evaluation
- Select a connected topology and choose at least 3 runs per RTT condition
- Run the experiment for the built-in 20, 100, and 200 ms RTT conditions
- Review mean and sample standard deviation, then download summary or per-run CSVs
- Interpret convergence delay as a model (update iterations × RTT), not measured real-network latency

##  Algorithm Explanations

### Dijkstra's Algorithm (Link-State)
```
1. Initialize: dist[source]=0, all others=∞
2. While unvisited nodes exist:
   a. Pick unvisited node with minimum distance
   b. For each neighbor: relax edge
   c. Mark node visited
3. Result: shortest paths from source to all
```
Time: O((V+E) log V) with binary heap

### Bellman-Ford (Distance-Vector)
```
D_x(y) = min_v [ c(x,v) + D_v(y) ]
```
- Each router maintains distance vector
- Exchanges with neighbors iteratively
- Converges when no changes

### RIP Specifics
- Metric: hop count (1 per link)
- Maximum: 15 hops (16 = unreachable)
- Updates: every 30 seconds (periodic)
- Loop prevention: split horizon, poisoned reverse

##  Sample Scenarios

| Scenario | Routers | Links | Purpose |
|----------|---------|-------|---------|
| Simple Three | 3 | 3 | Basic triangle, fundamental behavior |
| Multiple Paths | 5 | 7 | Alternative path selection |
| Cost vs Hops | 4 | 4 | Metric difference demonstration |
| DV Loop | 3 | 3 | Count-to-infinity setup |
| Link Failure | 4 | 4 | Failure recovery |
| Disconnected | 4 | 2 | Unreachable destinations |
| RIP Example | 4 | 5 | Hop-count vs cost |
| Larger Network | 8 | 14 | Performance testing |

##  Limitations

1. **Educational Focus**: Not a production routing daemon
2. **No Real Protocol Packets**: Simulates logic, not wire format
3. **Single-Threaded**: Python GIL limits performance
4. **No FRRouting Integration**: Optional, not implemented
5. **Static Topology During Run**: Changes require re-run
6. **Memory**: Full topology stored per router (LS)
7. **IPv4 Only**: No IPv6 support in current version

##  Future Enhancements

- [ ] **FRRouting Integration** - Docker-based real OSPF validation
- [ ] **BGP Simulation** - Path vector protocol
- [ ] **Animation** - Packet forwarding visualization
- [ ] **Multi-Area OSPF** - Area hierarchy simulation
- [ ] **QoS Metrics** - Bandwidth, delay, reliability
- [ ] **Mobile/Ad-hoc** - AODV, DSR protocols
- [ ] **SDN Controller** - OpenFlow simulation
- [ ] **Export to NS-3** - Network simulator integration
- [ ] **Collaborative Mode** - Multi-user topology editing
- [ ] **Assessment Mode** - Auto-graded lab exercises

##  License

MIT License - Feel free to use for educational purposes.

##  Contributing

This is an educational project. Suggestions and improvements welcome!

##  Support

For issues or questions:
- Check the "Testing & About" page in the app
- Review test output for debugging
- Ensure virtual environment is activated

---

**Built for Computer Networks Education** 🎓
