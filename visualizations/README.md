# Career OS — Interactive Visualizations

Two algorithmic art pieces built with p5.js that visualize the Career OS system.

## Files

### `career-os-codebase-graph.html`
**Codebase Architecture Graph** — Force-directed graph of all 42 backend modules.
- Node size = lines of code
- Edge weight = import relationships
- 4 layers: Infrastructure / Intelligence / Routes / Support
- Hover any node for details
- Signal particles trace runtime execution paths

### `career-os-intelligence-network.html`
**Career Intelligence Network** — Algorithmic visualization of the memory system.
- Nodes represent career events (applications, skills, interviews, offers)
- Memory decay over time (nodes fade without reinforcement)
- Signal particles represent intelligence flowing between events
- Central hub = the Orchestrator

## Usage
Open any `.html` file directly in a browser — fully self-contained, no server needed.
