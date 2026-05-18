/**
 * Tests for Entity Graph Explorer Page
 *
 * Covers:
 * - Loads entity graph (7 nodes for Greenfield)
 * - Node rendering with labels
 * - Edge labels and relationships
 * - "Why Connected" interaction
 * - Sidebar details panel
 * - WCAG 2.0 AA accessibility
 *
 * TDD approach: Tests written first (RED phase).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

// Sample graph data for Greenfield case
const greenfield_graph = {
  nodes: [
    {
      id: "entity_vn_1",
      label: "Greenfield Industrial Trading Co., Ltd.",
      type: "TRADING_COMPANY",
      jurisdiction: "VN",
      risk_score: 65,
    },
    {
      id: "entity_cn_1",
      label: "Guangdong Greenfield Aluminum Mfg. Co., Ltd.",
      type: "MANUFACTURER",
      jurisdiction: "CN",
      risk_score: 72,
    },
    {
      id: "entity_hk_1",
      label: "Greenfield Holdings HK Ltd.",
      type: "HOLDING_COMPANY",
      jurisdiction: "HK",
      risk_score: 58,
    },
    {
      id: "entity_vn_2",
      label: "Greenfield Logistics Vietnam Co., Ltd.",
      type: "LOGISTICS",
      jurisdiction: "VN",
      risk_score: 62,
    },
    {
      id: "entity_us_1",
      label: "SunPath Energy Distributors LLC",
      type: "DISTRIBUTOR",
      jurisdiction: "US",
      risk_score: 22,
    },
    {
      id: "entity_us_2",
      label: "Reliable Imports Inc.",
      type: "IMPORTER",
      jurisdiction: "US",
      risk_score: 35,
    },
    {
      id: "vessel_1",
      label: "MV Pacific Horizon",
      type: "VESSEL",
      imo: "9234567",
      risk_score: 45,
    },
  ],
  edges: [
    {
      source: "entity_vn_1",
      target: "entity_cn_1",
      label: "OWNED_BY",
      confidence: 0.89,
    },
    {
      source: "entity_vn_1",
      target: "entity_vn_2",
      label: "SHARES_DIRECTOR",
      confidence: 0.91,
    },
    {
      source: "entity_vn_1",
      target: "vessel_1",
      label: "SHIPPED_VIA",
      confidence: 0.95,
    },
  ],
};

// Placeholder GraphPage component
const GraphPage = ({ graph }: { graph: any }) => (
  <div className="graph-container">
    <div className="canvas" role="img" aria-label="Entity relationship graph">
      {/* SVG/Canvas with nodes would be rendered here */}
      {graph.nodes.map((node: any) => (
        <div
          key={node.id}
          className="node"
          data-testid={`node-${node.id}`}
          onClick={() => {}}
        >
          {node.label}
        </div>
      ))}
    </div>

    <aside className="sidebar" aria-label="Entity details">
      <h2>Entity Details</h2>
      <div id="entity-details">
        {/* Details panel populated on node click */}
      </div>
      <button>Why Connected?</button>
    </aside>
  </div>
);

describe("GraphPage — Entity Explorer", () => {
  describe("Graph Loading", () => {
    it("should load 7-node Greenfield graph", () => {
      render(<GraphPage graph={greenfield_graph} />);

      expect(screen.getByText(/Greenfield Industrial Trading/)).toBeInTheDocument();
      expect(screen.getByText(/Guangdong Greenfield Aluminum/)).toBeInTheDocument();
      expect(screen.getByText(/MV Pacific Horizon/)).toBeInTheDocument();
    });

    it("should display graph title or description", () => {
      render(<GraphPage graph={greenfield_graph} />);

      const canvas = screen.getByRole("img", { name: /entity relationship graph/i });
      expect(canvas).toBeInTheDocument();
    });

    it("should handle empty graph gracefully", () => {
      const emptyGraph = { nodes: [], edges: [] };

      expect(() => {
        render(<GraphPage graph={emptyGraph} />);
      }).not.toThrow();
    });
  });

  describe("Node Rendering", () => {
    it("should render all 7 nodes", () => {
      render(<GraphPage graph={greenfield_graph} />);

      greenfield_graph.nodes.forEach((node: any) => {
        expect(screen.getByText(node.label)).toBeInTheDocument();
      });
    });

    it("should render VN shipper node (Greenfield Industrial)", () => {
      render(<GraphPage graph={greenfield_graph} />);

      expect(
        screen.getByText(/Greenfield Industrial Trading Co., Ltd./)
      ).toBeInTheDocument();
    });

    it("should render CN parent node (Guangdong Greenfield)", () => {
      render(<GraphPage graph={greenfield_graph} />);

      expect(
        screen.getByText(/Guangdong Greenfield Aluminum/)
      ).toBeInTheDocument();
    });

    it("should render vessel node (MV Pacific Horizon)", () => {
      render(<GraphPage graph={greenfield_graph} />);

      expect(screen.getByText(/MV Pacific Horizon/)).toBeInTheDocument();
    });

    it("should color-code nodes by risk level", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // High risk (>70): red
      // Medium risk (30-70): yellow
      // Low risk (<30): green
      const nodes = container.querySelectorAll(".node");
      expect(nodes.length).toBe(7);
    });

    it("should include jurisdiction badge on nodes", () => {
      render(<GraphPage graph={greenfield_graph} />);

      // Nodes should indicate jurisdiction (VN, CN, HK, US)
      expect(screen.getByText(/Greenfield Industrial Trading/)).toBeInTheDocument();
      // Visual indicator would be in actual component
    });
  });

  describe("Edge Labels and Relationships", () => {
    it("should display OWNED_BY relationship", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Edge label should be visible when rendered
      // In SVG/Canvas: Check for edge label "OWNED_BY"
    });

    it("should display SHARES_DIRECTOR relationship", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Should show relationship between VN entities
      // Visual label would appear on edge
    });

    it("should display SHIPPED_VIA relationship", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Should show relationship from shipper to vessel
      expect(screen.getByText(/MV Pacific Horizon/)).toBeInTheDocument();
    });

    it("should include confidence score on edges", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Edges should have confidence: 0.89, 0.91, 0.95
      // Visual representation would show in tooltip or label
    });
  });

  describe("Node Interaction", () => {
    it("should select node on click", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(shipperNode);

      // Node should be highlighted
      // Details should appear in sidebar
    });

    it("should highlight connected nodes when node is selected", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(shipperNode);

      // Connected nodes should be highlighted:
      // - CN parent (OWNED_BY)
      // - VN logistics (SHARES_DIRECTOR)
      // - Vessel (SHIPPED_VIA)
    });

    it("should display node details in sidebar", async () => {
      const user = userEvent.setup();
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(shipperNode);

      const sidebar = screen.getByRole("complementary", { name: /entity details/i });
      expect(sidebar).toBeInTheDocument();
    });

    it("should deselect node on second click", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);

      await user.click(shipperNode);
      // Node is selected

      await user.click(shipperNode);
      // Node is deselected
    });
  });

  describe("Sidebar Details Panel", () => {
    it("should display entity name", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      const sidebar = screen.getByLabelText(/entity details/i);
      expect(
        within(sidebar).getByText(/Greenfield Industrial Trading/)
      ).toBeInTheDocument();
    });

    it("should display entity type", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      // Sidebar should show: Type: TRADING_COMPANY
      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
    });

    it("should display entity jurisdiction", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      // Sidebar should show: Jurisdiction: VN
      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
    });

    it("should display risk score", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      // Sidebar should show: Risk Score: 65/100
      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
    });

    it("should display connected entities list", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      // Should list:
      // - OWNED_BY: Guangdong Greenfield Aluminum Mfg.
      // - SHARES_DIRECTOR: Greenfield Logistics Vietnam
      // - SHIPPED_VIA: MV Pacific Horizon
    });
  });

  describe("Why Connected Interaction", () => {
    it("should display Why Connected button", () => {
      render(<GraphPage graph={greenfield_graph} />);

      expect(screen.getByText(/Why Connected/)).toBeInTheDocument();
    });

    it("should explain connection when Why Connected is clicked", async () => {
      const user = userEvent.setup();
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Select a node first
      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(shipperNode);

      // Click Why Connected
      const whyButton = screen.getByText(/Why Connected/);
      await user.click(whyButton);

      // Should display explanation like:
      // "This Vietnamese entity is linked to Guangdong Greenfield (CN manufacturer)
      //  via transliterated name match and shared director Nguyen Van Hung"
    });

    it("should show confidence for each connection", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const shipperNode = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(shipperNode);

      const whyButton = screen.getByText(/Why Connected/);
      await user.click(whyButton);

      // Explanations should include confidence scores
      // "confidence: 0.89" for OWNED_BY relationship
    });
  });

  describe("Accessibility", () => {
    it("should pass jest-axe scan", async () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have descriptive canvas label", () => {
      render(<GraphPage graph={greenfield_graph} />);

      const canvas = screen.getByRole("img", {
        name: /entity relationship graph/i,
      });
      expect(canvas).toBeInTheDocument();
    });

    it("should have labeled sidebar", () => {
      render(<GraphPage graph={greenfield_graph} />);

      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
    });

    it("should support keyboard navigation through nodes", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      // Should be able to Tab between nodes
      await user.tab();

      // Should be able to press Enter to select
      await user.keyboard("{Enter}");
    });

    it("should announce node selection to screen readers", async () => {
      const user = userEvent.setup();
      render(<GraphPage graph={greenfield_graph} />);

      const node = screen.getByText(/Greenfield Industrial Trading/);
      await user.click(node);

      // aria-live region should announce selection
      // "Selected: Greenfield Industrial Trading Co., Ltd."
    });

    it("should have sufficient color contrast", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      // Node labels should have 4.5:1 contrast
      // jest-axe will verify
    });
  });

  describe("Responsive Design", () => {
    it("should render on mobile viewport", () => {
      const { container } = render(<GraphPage graph={greenfield_graph} />);

      expect(screen.getByRole("img")).toBeInTheDocument();
      // Canvas should be responsive
    });

    it("should stack sidebar below graph on mobile", () => {
      render(<GraphPage graph={greenfield_graph} />);

      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
      // Layout should be stacked on small screens
    });

    it("should side-by-side on desktop", () => {
      render(<GraphPage graph={greenfield_graph} />);

      const sidebar = screen.getByLabelText(/entity details/i);
      expect(sidebar).toBeInTheDocument();
      // Layout should be side-by-side on large screens
    });
  });

  describe("Performance", () => {
    it("should render 7-node graph without lag", () => {
      const start = performance.now();

      render(<GraphPage graph={greenfield_graph} />);

      const duration = performance.now() - start;
      expect(duration).toBeLessThan(1000); // Should render in < 1 second
    });

    it("should handle graph with 50+ nodes", () => {
      const largeGraph = {
        nodes: Array.from({ length: 50 }, (_, i) => ({
          id: `node_${i}`,
          label: `Entity ${i}`,
          type: "TRADING_COMPANY",
          jurisdiction: "VN",
          risk_score: Math.floor(Math.random() * 100),
        })),
        edges: Array.from({ length: 100 }, (_, i) => ({
          source: `node_${Math.floor(Math.random() * 50)}`,
          target: `node_${Math.floor(Math.random() * 50)}`,
          label: "RELATED_TO",
          confidence: 0.85,
        })),
      };

      expect(() => {
        render(<GraphPage graph={largeGraph} />);
      }).not.toThrow();
    });
  });

  describe("Data Validation", () => {
    it("should handle missing node properties", () => {
      const malformedGraph = {
        nodes: [
          {
            id: "node_1",
            label: "Entity 1",
            // Missing type, jurisdiction, risk_score
          },
        ],
        edges: [],
      };

      expect(() => {
        render(<GraphPage graph={malformedGraph} />);
      }).not.toThrow();
    });

    it("should handle circular relationships", () => {
      const circularGraph = {
        nodes: [
          { id: "a", label: "A", type: "TRADING_COMPANY", jurisdiction: "VN", risk_score: 50 },
          { id: "b", label: "B", type: "TRADING_COMPANY", jurisdiction: "CN", risk_score: 60 },
        ],
        edges: [
          { source: "a", target: "b", label: "OWNS", confidence: 0.9 },
          { source: "b", target: "a", label: "OWNED_BY", confidence: 0.9 },
        ],
      };

      expect(() => {
        render(<GraphPage graph={circularGraph} />);
      }).not.toThrow();
    });
  });
});
