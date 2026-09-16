import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

/** A disclosure of ordinary buttons; native summary supplies keyboard access. */
export default function EquipmentMenu({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => { if (ref.current && !ref.current.contains(event.target as Node)) ref.current.open = false; };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && ref.current?.open) {
        event.preventDefault(); event.stopPropagation();
        ref.current.open = false; ref.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", escape, true);
    return () => { document.removeEventListener("pointerdown", closeOutside); document.removeEventListener("keydown", escape, true); };
  }, []);
  return <details className="equipment-menu" ref={ref} onToggle={event => {
    const element = event.currentTarget;
    const panel = element.querySelector<HTMLElement>(":scope > div");
    if (element.open && panel) {
      const anchor = element.getBoundingClientRect();
      const width = panel.getBoundingClientRect().width;
      panel.style.left = `${Math.max(12, Math.min(anchor.left, window.innerWidth - width - 12)) - anchor.left}px`;
    }
  }}>
    <summary className="action-secondary">{t("equipmentSimple.more")}<span aria-hidden>⌄</span></summary>
    <div onClick={event => { if ((event.target as HTMLElement).closest("button") && ref.current) ref.current.open = false; }}>{children}</div>
  </details>;
}
