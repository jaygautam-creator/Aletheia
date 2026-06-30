import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import Home from "@/app/page";

afterEach(cleanup);

it("links to the live verification view", () => {
  render(<Home />);
  const cta = screen.getByRole("link", { name: /Try the live verification/ });
  expect(cta.getAttribute("href")).toBe("/verify");
});

it("lists the pipeline in execution order, Retriever first and Guardrail last", () => {
  render(<Home />);
  const stages = screen
    .getByLabelText(/verification pipeline/i)
    .querySelectorAll("li span.font-medium");
  const names = Array.from(stages).map((el) => el.textContent);
  expect(names).toEqual(["Retriever", "Generator", "Verifier", "Aggregator", "Guardrail"]);
});
