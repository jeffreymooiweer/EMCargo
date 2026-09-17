/**
 * A failed card lookup must not masquerade as an installation refusing to share
 * cards. Retrying preserves the requested regulation and missing-card facts.
 * Authentication of this route is covered at the application boundary.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, expect, it, vi } from "vitest";
import CardsPage from "./CardsPage";
const api = vi.hoisted(() => ({ cardLookup: vi.fn() }));
vi.mock("../api/client", () => ({ api }));
vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../components/BrandLockup", () => ({ default: () => <span>EMCargo</span> }));
beforeEach(() => vi.clearAllMocks());

it("retries the requested card lookup and retains explicit missing cards", async () => {
  api.cardLookup.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ cards: [
    { un_number: "1203", available: true }, { un_number: "1263", available: false },
  ] });
  render(<MemoryRouter initialEntries={["/cards?un=1203,1263&m=imdg"]}><CardsPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("cards.loadFailed");
  await userEvent.click(screen.getByRole("button", { name: "overview.retry" }));
  expect(await screen.findByText("UN 1203")).toBeVisible();
  expect(screen.getByText("UN 1263")).toBeVisible();
  expect(screen.getByText("cards.missing")).toBeVisible();
  expect(screen.getByRole("link", { name: "cards.open" })).toHaveAttribute("href", "/api/cards/1203/IMDG.pdf");
  expect(api.cardLookup).toHaveBeenLastCalledWith("1203,1263", "IMDG");
  await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
});
