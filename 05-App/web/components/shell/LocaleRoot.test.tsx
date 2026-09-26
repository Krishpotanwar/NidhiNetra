import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test } from "vitest";
import { setLocale } from "@/lib/strings";
import { LocaleRoot } from "./LocaleRoot";
import { LanguageToggle } from "./LanguageToggle";
import { Str } from "./Str";

function renderHeader() {
  return render(
    <LocaleRoot>
      <LanguageToggle />
      <Str k="nav.dashboard" />
    </LocaleRoot>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.lang = "en";
});

afterEach(() => {
  setLocale("en");
});

test("starts in English, matching the server-rendered html[lang]", () => {
  renderHeader();
  expect(screen.getByText("Dashboard")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("en");
});

test("clicking the toggle renders nav in Hindi and sets html[lang] to hi", () => {
  renderHeader();

  fireEvent.click(screen.getByRole("button", { name: /language/i }));

  expect(screen.getByText("डैशबोर्ड")).toBeInTheDocument();
  expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
  expect(document.documentElement.lang).toBe("hi");
});

test("clicking the toggle again restores English and html[lang]", () => {
  renderHeader();
  const toggle = () => screen.getByRole("button", { name: /language/i });

  fireEvent.click(toggle());
  expect(screen.getByText("डैशबोर्ड")).toBeInTheDocument();

  fireEvent.click(toggle());
  expect(screen.getByText("Dashboard")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("en");
});

test("a stored hi preference (nn.locale) is applied on mount", async () => {
  window.localStorage.setItem("nn.locale", "hi");
  renderHeader();
  expect(await screen.findByText("डैशबोर्ड")).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("hi");
});
