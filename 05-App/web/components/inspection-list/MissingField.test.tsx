import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { MissingField } from "./MissingField";
import { STRINGS } from "@/lib/strings";

test.each(["vendor", "date", "amount", "agency", "generic"] as const)(
  "renders the frozen contracts/strings.json copy for '%s'",
  (field) => {
    render(<MissingField field={field} />);
    expect(screen.getByText(STRINGS.missing_fields[field])).toBeInTheDocument();
  },
);
