import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import {EmptyState, ErrorState, Status} from "./query-state";

describe("query states", () => {
  it("renders useful empty-state guidance", () => {
    render(<EmptyState title="No providers" detail="Register a provider." />);
    expect(screen.getByText("No providers")).toBeInTheDocument();
    expect(screen.getByText("Register a provider.")).toBeInTheDocument();
  });

  it("renders API error detail", () => {
    render(<ErrorState error={new Error("Permission denied")} />);
    expect(screen.getByText("Permission denied")).toBeInTheDocument();
  });

  it("pairs status color with readable text", () => {
    render(<Status value="dead_lettered" />);
    expect(screen.getByText("dead lettered")).toBeInTheDocument();
  });
});
