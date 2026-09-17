/**
 * Substance and packaging suggestions used to commit only on mousedown, so a
 * keyboard user could neither reach nor select a result. Closing the field also
 * failed to invalidate requests: an old substance list could reappear later.
 * These cases exercise the input as a user does and verify that only a current,
 * explicitly selected result reaches the dangerous-goods form.
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SuggestInput, { SuggestItem } from "./SuggestInput";

const entries: SuggestItem<string>[] = [
  { key: "1202", data: "1202", render: "UN 1202 Diesel" },
  { key: "1203", data: "1203", render: "UN 1203 Petrol" },
];

function Harness({ onPick, fetcher = async () => entries }: {
  onPick: (value: string) => void;
  fetcher?: (query: string) => Promise<SuggestItem<string>[]>;
}) {
  const [value, setValue] = useState("");
  return <><label htmlFor="substance">Substance</label><SuggestInput id="substance" ariaLabel="Substance"
    value={value} onChange={setValue} onPick={item => { setValue(item); onPick(item); }} fetcher={fetcher} />
    <button type="button">Next field</button></>;
}

afterEach(() => vi.useRealTimers());

describe("SuggestInput", () => {
  it("selects a substance with arrows and Enter without moving keyboard focus", async () => {
    const onPick = vi.fn();
    const user = userEvent.setup();
    render(<Harness onPick={onPick} />);
    const input = screen.getByRole("combobox", { name: "Substance" });
    await user.type(input, "12");
    await screen.findByRole("option", { name: "UN 1202 Diesel" });
    await user.keyboard("{ArrowDown}{ArrowDown}{Enter}");
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("1203");
    expect(input).toHaveValue("1203");
    expect(input).toHaveFocus();
    expect(input).toHaveAttribute("aria-expanded", "false");
  });

  it("accepts a click or touch-generated click and preserves free text on Tab", async () => {
    const onPick = vi.fn();
    const user = userEvent.setup();
    render(<Harness onPick={onPick} />);
    const input = screen.getByRole("combobox", { name: "Substance" });
    await user.type(input, "12");
    fireEvent.click(await screen.findByRole("option", { name: "UN 1202 Diesel" }));
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick).toHaveBeenCalledWith("1202");
    await user.clear(input);
    await user.type(input, "Own substance");
    await screen.findByRole("option", { name: "UN 1202 Diesel" });
    await user.tab();
    expect(input).toHaveValue("Own substance");
    expect(screen.getByRole("button", { name: "Next field" })).toHaveFocus();
    expect(onPick).toHaveBeenCalledTimes(1);
  });

  it("discards an in-flight result after Escape instead of reopening stale suggestions", async () => {
    vi.useFakeTimers();
    let resolve!: (value: SuggestItem<string>[]) => void;
    const fetcher = vi.fn(() => new Promise<SuggestItem<string>[]>(done => { resolve = done; }));
    render(<Harness onPick={vi.fn()} fetcher={fetcher} />);
    const input = screen.getByRole("combobox", { name: "Substance" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "12" } });
    await act(async () => { vi.advanceTimersByTime(250); });
    expect(fetcher).toHaveBeenCalledOnce();
    fireEvent.keyDown(input, { key: "Escape" });
    await act(async () => { resolve(entries); });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(input).toHaveValue("12");
    expect(input).toHaveAttribute("aria-expanded", "false");
  });
});
