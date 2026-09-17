import type { CargoGood, CargoManifest, PackagingTemplate } from "../../api/cargo";
import type { EquipmentSnapshot } from "../../api/client";
import CargoWorkspace from "./CargoWorkspace";

const templates: PackagingTemplate[] = [];
const equipment: EquipmentSnapshot[] = [];
const readonly = () => undefined;

/** The reviewer reads exactly the saved tree; no editor or catalogue requests. */
export default function CargoSummary({ value, goods }: { value: CargoManifest; goods: CargoGood[] }) {
  return <CargoWorkspace value={value} goods={goods} onChange={readonly} disabled templates={templates} equipment={equipment} />;
}
