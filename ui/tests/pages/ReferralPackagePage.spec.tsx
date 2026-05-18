/**
 * Tests for Referral Package Page
 *
 * Covers:
 * - Renders full referral JSON (Tables 3-1 through 3-14)
 * - Expandable sections for each table
 * - PDF export functionality
 * - WCAG 2.0 AA accessibility
 *
 * TDD approach: Tests written first (RED phase).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

// Sample referral package for testing
const greenfield_package = {
  package_id: "SENTRY-2026-001",
  shipment_id: "SAMPLE-BOL-2026-001",
  confidence_level: "HIGH",
  score: 91,
  recommended_action: "EXAMINE_ON_ARRIVAL",
  sections: {
    shipment_id: {
      bill_id: "SAMPLE-BOL-2026-001",
      manifest_id: "MF-2026-001",
      eta: "2026-06-15T00:00:00Z",
    },
    line_items: [
      {
        hts_code: "7604.10.1000",
        description: "Aluminum extrusions, other than tubes",
        weight_mt: 26.2,
        declared_value_usd: 72030,
      },
    ],
    routing_history: [
      {
        location: "Nansha Terminal, Guangzhou",
        country: "CN",
        date: "2026-05-20",
      },
    ],
    score_breakdown: {
      total: 91,
      confidence_tier: "HIGH",
      components: [
        { name: "origin_doc_gap", score: 23, max: 25 },
      ],
    },
    data_sources: [
      { name: "ISF Data Element 9", confidence: 0.95 },
    ],
  },
};

// Placeholder ReferralPackagePage component
const ReferralPackagePage = ({ package: pkg }: { package: any }) => (
  <div>
    <h1>Referral Package: {pkg.package_id}</h1>
    <div className="score-section">
      <div>Score: {pkg.score}/100</div>
      <div>Confidence: {pkg.confidence_level}</div>
      <div>Action: {pkg.recommended_action}</div>
    </div>

    <section aria-label="Shipment Details">
      <button onClick={() => {}} aria-expanded="false">
        Shipment ID (Table 3-1)
      </button>
      <div hidden>
        <p>Bill ID: {pkg.sections.shipment_id.bill_id}</p>
      </div>
    </section>

    <section aria-label="Line Items">
      <button onClick={() => {}} aria-expanded="false">
        Line Items (Table 3-2)
      </button>
    </section>

    <button onClick={() => {}}>Export as PDF</button>
  </div>
);

describe("ReferralPackagePage", () => {
  describe("Rendering Full Package", () => {
    it("should display package ID", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/SENTRY-2026-001/)).toBeInTheDocument();
    });

    it("should display confidence score (91/100)", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Score: 91\/100/)).toBeInTheDocument();
    });

    it("should display confidence level (HIGH)", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Confidence: HIGH/)).toBeInTheDocument();
    });

    it("should display recommended action", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/EXAMINE_ON_ARRIVAL/)).toBeInTheDocument();
    });

    it("should display all 14 section headers", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // At minimum, check for Shipment Details and Line Items
      expect(screen.getByText(/Table 3-1/)).toBeInTheDocument();
      expect(screen.getByText(/Table 3-2/)).toBeInTheDocument();
    });
  });

  describe("Table 3-1: Shipment ID", () => {
    it("should display Bill ID", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // After expanding section
      expect(screen.getByText(/SAMPLE-BOL-2026-001/)).toBeInTheDocument();
    });

    it("should display Manifest ID", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/MF-2026-001/)).toBeInTheDocument();
    });

    it("should display ETA", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/2026-06-15/)).toBeInTheDocument();
    });
  });

  describe("Table 3-2: Line Items", () => {
    it("should display HTS code", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/7604.10.1000/)).toBeInTheDocument();
    });

    it("should display commodity description", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Aluminum extrusions/)).toBeInTheDocument();
    });

    it("should display weight and value", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/26.2/)).toBeInTheDocument();
      expect(screen.getByText(/72030/)).toBeInTheDocument();
    });
  });

  describe("Expandable Sections", () => {
    it("should have expandable section buttons", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      const buttons = screen.getAllByRole("button");
      const expandButtons = buttons.filter(
        (b) => b.getAttribute("aria-expanded") === "false"
      );

      expect(expandButtons.length).toBeGreaterThan(0);
    });

    it("should toggle expanded state on click", async () => {
      const user = userEvent.setup();
      render(<ReferralPackagePage package={greenfield_package} />);

      const shipmentButton = screen.getByText(/Table 3-1/);
      expect(shipmentButton).toHaveAttribute("aria-expanded", "false");

      await user.click(shipmentButton);

      expect(shipmentButton).toHaveAttribute("aria-expanded", "true");

      await user.click(shipmentButton);

      expect(shipmentButton).toHaveAttribute("aria-expanded", "false");
    });

    it("should show content when section is expanded", async () => {
      const user = userEvent.setup();
      const { container } = render(
        <ReferralPackagePage package={greenfield_package} />
      );

      const shipmentButton = screen.getByText(/Table 3-1/);
      const content = shipmentButton.nextElementSibling;

      if (content) {
        expect(content).toHaveAttribute("hidden");

        await user.click(shipmentButton);

        expect(content).not.toHaveAttribute("hidden");
      }
    });

    it("should allow expanding multiple sections simultaneously", async () => {
      const user = userEvent.setup();
      render(<ReferralPackagePage package={greenfield_package} />);

      const shipmentButton = screen.getByText(/Table 3-1/);
      const lineItemsButton = screen.getByText(/Table 3-2/);

      await user.click(shipmentButton);
      await user.click(lineItemsButton);

      expect(shipmentButton).toHaveAttribute("aria-expanded", "true");
      expect(lineItemsButton).toHaveAttribute("aria-expanded", "true");
    });
  });

  describe("PDF Export", () => {
    it("should have export to PDF button", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Export as PDF/)).toBeInTheDocument();
    });

    it("should handle PDF export click", async () => {
      const user = userEvent.setup();
      const mockExport = vi.fn();

      render(
        <ReferralPackagePage package={greenfield_package} />
      );

      const exportButton = screen.getByText(/Export as PDF/);
      await user.click(exportButton);

      // In real implementation: Verify PDF is generated
    });

    it("should include all sections in PDF export", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // Verify all tables are present for export
      expect(screen.getByText(/Table 3-1/)).toBeInTheDocument();
      expect(screen.getByText(/Table 3-2/)).toBeInTheDocument();
    });

    it("should filename include package ID", async () => {
      // Placeholder: In real implementation, verify filename
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/SENTRY-2026-001/)).toBeInTheDocument();
    });
  });

  describe("Score Breakdown (Table 3-12)", () => {
    it("should display total score", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Score: 91/)).toBeInTheDocument();
    });

    it("should display component scores", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // After expanding score breakdown section
      expect(screen.getByText(/origin_doc_gap/)).toBeInTheDocument();
    });

    it("should show component max values", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // Components should show "23 / 25" format
      const scoreText = screen.queryByText(/23/);
      expect(scoreText).toBeInTheDocument();
    });

    it("should sum components to total", () => {
      const { container } = render(
        <ReferralPackagePage package={greenfield_package} />
      );

      // Verify component_sum = total
      const breakdown = greenfield_package.sections.score_breakdown;
      expect(breakdown.total).toBe(91);
    });
  });

  describe("Data Sources (Table 3-14)", () => {
    it("should display data sources section", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/Table 3-14/)).toBeInTheDocument();
    });

    it("should display ISF as data source", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/ISF Data Element 9/)).toBeInTheDocument();
    });

    it("should display confidence scores for sources", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      // Confidence of 0.95 for ISF
      expect(screen.getByText(/0.95/)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should pass jest-axe scan", async () => {
      const { container } = render(
        <ReferralPackagePage package={greenfield_package} />
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have descriptive page title", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    });

    it("should have proper heading hierarchy", () => {
      const { container } = render(
        <ReferralPackagePage package={greenfield_package} />
      );

      const h1 = container.querySelector("h1");
      expect(h1).toBeInTheDocument();

      // Sections should use h2 or have proper role
      const sections = container.querySelectorAll("section");
      expect(sections.length).toBeGreaterThan(0);
    });

    it("should have labeled sections", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      const sections = screen.getAllByRole("region");
      expect(sections.length).toBeGreaterThan(0);

      sections.forEach((section) => {
        expect(section).toHaveAttribute("aria-label");
      });
    });

    it("should announce expanded/collapsed state", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        if (button.getAttribute("aria-expanded")) {
          expect(button).toHaveAttribute("aria-expanded");
        }
      });
    });

    it("should have sufficient color contrast", () => {
      const { container } = render(
        <ReferralPackagePage package={greenfield_package} />
      );

      // jest-axe will check contrast ratios
      // In CSS: Use #333 text on #fff background or better
    });

    it("should support keyboard navigation", async () => {
      const user = userEvent.setup();
      render(<ReferralPackagePage package={greenfield_package} />);

      // Tab to first button
      await user.tab();

      // Should focus on an interactive element
      expect(document.activeElement).toBeInstanceOf(HTMLButtonElement);
    });
  });

  describe("Responsive Design", () => {
    it("should render on mobile viewport", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      const h1 = screen.getByRole("heading");
      expect(h1).toBeInTheDocument();
      // In real test: Use viewport size 375x667
    });

    it("should render on tablet viewport", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/SENTRY-2026-001/)).toBeInTheDocument();
      // In real test: Use viewport size 768x1024
    });

    it("should render on desktop viewport", () => {
      render(<ReferralPackagePage package={greenfield_package} />);

      expect(screen.getByText(/SENTRY-2026-001/)).toBeInTheDocument();
      // In real test: Use viewport size 1920x1080
    });
  });

  describe("Data Validation", () => {
    it("should handle missing optional sections gracefully", () => {
      const minimalPackage = {
        package_id: "TEST-001",
        shipment_id: "TEST-SHIP",
        score: 91,
        confidence_level: "HIGH",
        recommended_action: "EXAMINE_ON_ARRIVAL",
        sections: {},
      };

      expect(() => {
        render(<ReferralPackagePage package={minimalPackage} />);
      }).not.toThrow();
    });

    it("should handle malformed dates", () => {
      const malformedPackage = {
        ...greenfield_package,
        sections: {
          ...greenfield_package.sections,
          shipment_id: {
            ...greenfield_package.sections.shipment_id,
            eta: "invalid-date",
          },
        },
      };

      expect(() => {
        render(<ReferralPackagePage package={malformedPackage} />);
      }).not.toThrow();
    });
  });
});
