"""
Network Topology Module

Represents and manages network topologies for routing algorithm simulation.
Uses NetworkX for graph operations but maintains independent data structures.
"""

import networkx as nx
import uuid
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from copy import deepcopy
import json


@dataclass
class Router:
    """Represents a router in the network."""
    id: str
    name: str
    x: float = 0.0
    y: float = 0.0
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Router):
            return self.id == other.id
        return False


@dataclass
class Link:
    """Represents a link between two routers."""
    source: str
    target: str
    cost: float
    is_failed: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    def __hash__(self):
        return hash((self.source, self.target))
    
    def __eq__(self, other):
        if isinstance(other, Link):
            return (self.source == other.source and self.target == other.target) or \
                   (self.source == other.target and self.target == other.source)
        return False
    
    def get_other_end(self, router_id: str) -> Optional[str]:
        """Get the other endpoint of this link."""
        if self.source == router_id:
            return self.target
        elif self.target == router_id:
            return self.source
        return None


class NetworkTopology:
    """
    Manages a network topology with routers and links.
    Provides methods for building, modifying, and analyzing the network.
    """
    
    def __init__(self):
        self.routers: Dict[str, Router] = {}
        self.links: Dict[str, Link] = {}  # Key: "source-target" (sorted)
        self.graph = nx.Graph()
        self._next_router_id = 1
        self._layout_positions: Dict[str, Tuple[float, float]] = {}
    
    def add_router(self, name: str, x: float = 0.0, y: float = 0.0) -> Router:
        """Add a new router to the topology."""
        if any(r.name == name for r in self.routers.values()):
            raise ValueError(f"Router with name '{name}' already exists")
        
        router_id = f"R{self._next_router_id}"
        self._next_router_id += 1
        
        router = Router(id=router_id, name=name, x=x, y=y)
        self.routers[router_id] = router
        self.graph.add_node(router_id, name=name)
        # Clear cached layout so the new router gets a computed position
        self._layout_positions = {}
        return router
    
    def remove_router(self, router_id: str) -> bool:
        """Remove a router and all its links."""
        if router_id not in self.routers:
            return False
        
        # Remove all links connected to this router
        links_to_remove = [
            key for key, link in self.links.items()
            if link.source == router_id or link.target == router_id
        ]
        for key in links_to_remove:
            link = self.links[key]
            self.graph.remove_edge(link.source, link.target)
            del self.links[key]
        
        del self.routers[router_id]
        self.graph.remove_node(router_id)
        if router_id in self._layout_positions:
            del self._layout_positions[router_id]
        return True
    
    def add_link(self, source_id: str, target_id: str, cost: float) -> Link:
        """Add a link between two routers."""
        if source_id not in self.routers or target_id not in self.routers:
            raise ValueError("Both routers must exist in the topology")
        if source_id == target_id:
            raise ValueError("Cannot create self-loop")
        if cost <= 0:
            raise ValueError("Link cost must be positive")
        
        # Check for existing link (undirected)
        link_key = self._get_link_key(source_id, target_id)
        if link_key in self.links:
            raise ValueError(f"Link between {source_id} and {target_id} already exists")
        
        link = Link(source=source_id, target=target_id, cost=cost)
        self.links[link_key] = link
        self.graph.add_edge(source_id, target_id, weight=cost, link_id=link.id)
        return link
    
    def remove_link(self, link_id: str) -> bool:
        """Remove a link by its ID."""
        for key, link in self.links.items():
            if link.id == link_id:
                del self.links[key]
                self.graph.remove_edge(link.source, link.target)
                return True
        return False
    
    def update_link_cost(self, source_id: str, target_id: str, new_cost: float) -> bool:
        """Update the cost of an existing link."""
        if new_cost <= 0:
            raise ValueError("Link cost must be positive")
        
        link_key = self._get_link_key(source_id, target_id)
        if link_key not in self.links:
            return False
        
        link = self.links[link_key]
        link.cost = new_cost
        self.graph[source_id][target_id]['weight'] = new_cost
        return True
    
    def set_link_failed(self, source_id: str, target_id: str, failed: bool = True) -> bool:
        """Mark a link as failed or restore it."""
        link_key = self._get_link_key(source_id, target_id)
        if link_key not in self.links:
            return False
        
        link = self.links[link_key]
        link.is_failed = failed
        
        if failed:
            # Remove edge from graph for path computation
            if self.graph.has_edge(source_id, target_id):
                self.graph.remove_edge(source_id, target_id)
        else:
            # Restore edge
            self.graph.add_edge(source_id, target_id, weight=link.cost, link_id=link.id)
        return True
    
    def _get_link_key(self, source_id: str, target_id: str) -> str:
        """Generate a consistent key for an undirected link."""
        return f"{min(source_id, target_id)}-{max(source_id, target_id)}"
    
    def get_neighbors(self, router_id: str) -> List[Tuple[str, float]]:
        """Get all neighbors of a router with link costs."""
        neighbors = []
        for link in self.links.values():
            if link.is_failed:
                continue
            other = link.get_other_end(router_id)
            if other:
                neighbors.append((other, link.cost))
        return neighbors
    
    def get_link_cost(self, source_id: str, target_id: str) -> Optional[float]:
        """Get the cost of a direct link between two routers."""
        link_key = self._get_link_key(source_id, target_id)
        if link_key in self.links and not self.links[link_key].is_failed:
            return self.links[link_key].cost
        return None
    
    def get_all_routers(self) -> List[Router]:
        """Get list of all routers."""
        return list(self.routers.values())
    
    def get_all_links(self) -> List[Link]:
        """Get list of all links (including failed ones)."""
        return list(self.links.values())
    
    def get_active_links(self) -> List[Link]:
        """Get list of non-failed links."""
        return [link for link in self.links.values() if not link.is_failed]
    
    def is_connected(self) -> bool:
        """Check if the network is connected (ignoring failed links)."""
        active_routers = [r.id for r in self.routers.values()]
        if len(active_routers) <= 1:
            return True
        try:
            return nx.is_connected(self.graph)
        except:
            return False
    
    def get_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Get shortest path using NetworkX (for reference/validation)."""
        try:
            return nx.shortest_path(self.graph, source_id, target_id, weight='weight')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def get_shortest_path_length(self, source_id: str, target_id: str) -> Optional[float]:
        """Get shortest path length using NetworkX."""
        try:
            return nx.shortest_path_length(self.graph, source_id, target_id, weight='weight')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
    
    def compute_layout(self) -> Dict[str, Tuple[float, float]]:
        """Compute layout positions for visualization."""
        try:
            pos = nx.spring_layout(self.graph, seed=42, k=2, iterations=50)
            # Convert numpy arrays to tuples
            pos = {k: (float(v[0]), float(v[1])) for k, v in pos.items()}
            self._layout_positions = pos
            return pos
        except:
            # Fallback to circular layout
            pos = nx.circular_layout(self.graph)
            pos = {k: (float(v[0]), float(v[1])) for k, v in pos.items()}
            self._layout_positions = pos
            return pos
    
    def get_layout(self) -> Dict[str, Tuple[float, float]]:
        """Get layout positions, computing if necessary."""
        if not self._layout_positions:
            return self.compute_layout()
        return self._layout_positions
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize topology to dictionary."""
        return {
            'routers': {
                rid: {'name': r.name, 'x': r.x, 'y': r.y}
                for rid, r in self.routers.items()
            },
            'links': {
                key: {
                    'source': link.source,
                    'target': link.target,
                    'cost': link.cost,
                    'is_failed': link.is_failed,
                    'id': link.id
                }
                for key, link in self.links.items()
            },
            'next_router_id': self._next_router_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NetworkTopology':
        """Deserialize topology from dictionary."""
        topo = cls()
        topo._next_router_id = data.get('next_router_id', 1)
        
        for rid, rdata in data.get('routers', {}).items():
            router = Router(id=rid, name=rdata['name'], x=rdata.get('x', 0), y=rdata.get('y', 0))
            topo.routers[rid] = router
            topo.graph.add_node(rid, name=rdata['name'])
        
        for key, ldata in data.get('links', {}).items():
            link = Link(
                source=ldata['source'],
                target=ldata['target'],
                cost=ldata['cost'],
                is_failed=ldata.get('is_failed', False),
                id=ldata.get('id', str(uuid.uuid4())[:8])
            )
            topo.links[key] = link
            if not link.is_failed:
                topo.graph.add_edge(link.source, link.target, weight=link.cost, link_id=link.id)
        
        return topo
    
    def copy(self) -> 'NetworkTopology':
        """Create a deep copy of the topology."""
        return deepcopy(self)
    
    def __str__(self) -> str:
        lines = [f"NetworkTopology: {len(self.routers)} routers, {len(self.links)} links"]
        for rid, router in self.routers.items():
            lines.append(f"  {rid} ({router.name})")
        for link in self.links.values():
            status = " [FAILED]" if link.is_failed else ""
            lines.append(f"  {link.source} --({link.cost})-- {link.target}{status}")
        return "\n".join(lines)


def create_predefined_scenario(scenario_name: str) -> NetworkTopology:
    """Create a predefined network scenario."""
    topo = NetworkTopology()
    
    if scenario_name == "simple_three":
        # Simple 3-router network
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        topo.add_link(r1.id, r2.id, 1)
        topo.add_link(r2.id, r3.id, 1)
        topo.add_link(r1.id, r3.id, 3)
    
    elif scenario_name == "multiple_paths":
        # Network with multiple paths between endpoints
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        r4 = topo.add_router("R4")
        r5 = topo.add_router("R5")
        topo.add_link(r1.id, r2.id, 2)
        topo.add_link(r1.id, r3.id, 3)
        topo.add_link(r2.id, r4.id, 2)
        topo.add_link(r3.id, r4.id, 1)
        topo.add_link(r2.id, r5.id, 4)
        topo.add_link(r4.id, r5.id, 2)
        topo.add_link(r3.id, r5.id, 3)
    
    elif scenario_name == "cost_vs_hops":
        # Lowest-cost path differs from fewest-hop path
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        r4 = topo.add_router("R4")
        # Direct path: 2 hops, cost 10 (R1-R2-R4)
        topo.add_link(r1.id, r2.id, 5)
        topo.add_link(r2.id, r4.id, 5)
        # Alternative: 3 hops, cost 6 (R1-R3-R2-R4)
        topo.add_link(r1.id, r3.id, 2)
        topo.add_link(r3.id, r2.id, 2)
        # Update R2-R4 cost to 2 (making alternative path cost 6 vs direct 10)
        topo.update_link_cost(r2.id, r4.id, 2)
    
    elif scenario_name == "distance_vector_loop":
        # Classic DV loop scenario for count-to-infinity
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        topo.add_link(r1.id, r2.id, 1)
        topo.add_link(r2.id, r3.id, 1)
        topo.add_link(r1.id, r3.id, 10)  # High cost direct link
    
    elif scenario_name == "link_failure":
        # Network where link failure triggers recalculation
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        r4 = topo.add_router("R4")
        topo.add_link(r1.id, r2.id, 1)
        topo.add_link(r2.id, r3.id, 1)
        topo.add_link(r3.id, r4.id, 1)
        topo.add_link(r1.id, r4.id, 10)
    
    elif scenario_name == "disconnected":
        # Two disconnected components
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        r4 = topo.add_router("R4")
        topo.add_link(r1.id, r2.id, 1)
        topo.add_link(r3.id, r4.id, 1)
        # No link between {R1,R2} and {R3,R4}
    
    elif scenario_name == "rip_example":
        # Example showing RIP hop-count vs cost-based routing
        r1 = topo.add_router("R1")
        r2 = topo.add_router("R2")
        r3 = topo.add_router("R3")
        r4 = topo.add_router("R4")
        # Path 1: R1-R2-R4 (2 hops, cost 20)
        topo.add_link(r1.id, r2.id, 10)
        topo.add_link(r2.id, r4.id, 10)
        # Path 2: R1-R3-R4 (2 hops, cost 5)
        topo.add_link(r1.id, r3.id, 2)
        topo.add_link(r3.id, r4.id, 3)
        # Path 3: R1-R2-R3-R4 (3 hops, cost 4) - fewer cost but more hops
        topo.add_link(r2.id, r3.id, 1)
    
    elif scenario_name == "larger_network":
        # Larger network for performance testing
        for i in range(1, 9):
            topo.add_router(f"R{i}")
        # Create a mesh-like topology
        edges = [
            (1, 2, 2), (1, 3, 3), (2, 3, 1), (2, 4, 2),
            (3, 5, 2), (4, 5, 1), (4, 6, 3), (5, 6, 2),
            (5, 7, 1), (6, 8, 2), (7, 8, 1), (3, 4, 4),
            (2, 5, 5), (6, 7, 3)
        ]
        for u, v, cost in edges:
            topo.add_link(f"R{u}", f"R{v}", cost)
    
    else:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    return topo


def create_random_topology(num_routers: int, num_links: int, max_cost: float = 10.0, 
                           seed: Optional[int] = None) -> NetworkTopology:
    """Create a random connected network topology."""
    import random
    if seed is not None:
        random.seed(seed)
    
    topo = NetworkTopology()
    
    # Add routers
    for i in range(num_routers):
        topo.add_router(f"R{i+1}")
    
    router_ids = list(topo.routers.keys())
    
    # Ensure connectivity first - create a spanning tree
    shuffled = router_ids.copy()
    random.shuffle(shuffled)
    for i in range(1, len(shuffled)):
        cost = round(random.uniform(1.0, max_cost), 1)
        topo.add_link(shuffled[i-1], shuffled[i], cost)
    
    # Add remaining links
    links_added = num_routers - 1
    possible_links = []
    for i in range(len(router_ids)):
        for j in range(i+1, len(router_ids)):
            key = topo._get_link_key(router_ids[i], router_ids[j])
            if key not in topo.links:
                possible_links.append((router_ids[i], router_ids[j]))
    
    random.shuffle(possible_links)
    for source, target in possible_links:
        if links_added >= num_links:
            break
        cost = round(random.uniform(1.0, max_cost), 1)
        try:
            topo.add_link(source, target, cost)
            links_added += 1
        except ValueError:
            continue
    
    return topo