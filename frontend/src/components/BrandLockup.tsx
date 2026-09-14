import BrandName from "./BrandName";
import "./brand.css";

/** The website's mark and lettering share one cap height and baseline. */
export default function BrandLockup({ name, logo, compact = false }: {
  name?: string;
  logo?: string | null;
  compact?: boolean;
}) {
  const customName = Boolean(name && name !== "EMCargo");
  return <span className={`brand-lockup${customName ? " brand-lockup-custom" : ""}${compact ? " brand-lockup-compact" : ""}`}>
    <img className={`brand-symbol${logo ? " brand-symbol-custom" : ""}`} src={logo || "/emcargo.svg?v=2.11.1"} alt={compact ? name || "EMCargo" : ""} />
    {!compact && <span className="brand-wordmark"><BrandName name={name} /></span>}
  </span>;
}
