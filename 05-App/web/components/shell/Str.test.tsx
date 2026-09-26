import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Str } from "./Str";

test("renders the string at a dotted STRINGS path", () => {
  render(<Str k="nav.dashboard" />);
  expect(screen.getByText("Dashboard")).toBeInTheDocument();
});

test("renders nothing for a path that resolves to no string", () => {
  const { container } = render(<Str k="nav.not_a_real_key" />);
  expect(container).toBeEmptyDOMElement();
});

test("renders nothing for a path through a non-existent top-level block", () => {
  const { container } = render(<Str k="not_a_real_block.x" />);
  expect(container).toBeEmptyDOMElement();
});
