/** New shipments start with goods; transport preferences must not select documents. */
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { expect, it } from "vitest";
import ModalitySelectPage from "./ModalitySelectPage";
function Destination() { const location = useLocation(); return <output aria-label="Destination">{location.pathname}{location.search}</output>; }
it.each(["/", "/?choose=1", "/?input=paste", "/?input=document"])("starts preparation from %s", async path => {
 render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/" element={<ModalitySelectPage />} /><Route path="/wizard/:modality" element={<Destination />} /></Routes></MemoryRouter>);
 expect(await screen.findByLabelText("Destination")).toHaveTextContent(`/wizard/preparation${path.includes("input=") ? path.slice(1) : ""}`);
});
