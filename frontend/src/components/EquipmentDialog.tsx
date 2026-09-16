import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

export default function EquipmentDialog({ title, children, footer, onClose }: { title: string; children: React.ReactNode; footer?: React.ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { t } = useTranslation();
  useEffect(() => {
    const previous = document.activeElement;
    const element = dialog.current;
    element?.showModal();
    return () => {
      element?.close();
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus({ preventScroll: true });
    };
  }, []);
  return <dialog ref={dialog} className="equipment-dialog" aria-label={title} onCancel={event => { event.preventDefault(); onClose(); }} onClick={event => { if (event.target === dialog.current) onClose(); }}>
    <header><h3>{title}</h3><button type="button" className="equipment-close" aria-label={t("assets.close")} onClick={onClose}><span aria-hidden>×</span></button></header>
    <div className="equipment-dialog-body">{children}</div>
    {footer && <footer className="equipment-dialog-footer">{footer}</footer>}
  </dialog>;
}
