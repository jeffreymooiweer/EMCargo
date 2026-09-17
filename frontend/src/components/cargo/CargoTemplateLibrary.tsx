import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { User } from "../../api/client";
import { cargoApi, type PackagingTemplate } from "../../api/cargo";
import { canManage } from "../../permissions";
import EquipmentDialog from "../EquipmentDialog";
import EquipmentMenu from "../EquipmentMenu";
import { LayersIcon, PlusIcon, SearchIcon } from "../icons";
import CargoUnitFields, { blankTemplate } from "./CargoUnitFields";
import "./cargo.css";

export default function CargoTemplateLibrary({ user }: { user?: User }) {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<PackagingTemplate[]>([]);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<PackagingTemplate | null>(null);
  const [archived, setArchived] = useState<PackagingTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [retry, setRetry] = useState(0);
  const [limit, setLimit] = useState(50);
  const editable = canManage(user);
  const nameOf = (model: PackagingTemplate) => model.language_labels?.[i18n.language.slice(0, 2)] || model.name;
  const number = (value: number) => new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 3 }).format(value);
  useEffect(() => {
    let alive = true; setLoading(true); setError("");
    cargoApi.templates().then(data => { if (alive) setItems(data); }).catch(cause => { if (alive) setError(cause instanceof Error ? cause.message : t("cargo.errors.failed")); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [retry]);
  const filtered = items.filter(model => model.active !== false && `${nameOf(model)} ${model.name} ${t(`cargo.categories.${model.category}`)}`.toLowerCase().includes(query.toLowerCase()));
  const open = (model: PackagingTemplate) => { setFormError(""); setEditing({ ...model, name: nameOf(model) }); };
  return <div className="cargo-library page-enter">
    <div className="cargo-heading"><h2>{t("cargo.libraryTitle")}</h2>{editable && <button className="cargo-button cargo-primary" type="button" onClick={() => open(blankTemplate())}><PlusIcon />{t("cargo.addModel")}</button>}</div>
    <div className="cargo-search"><SearchIcon /><input type="search" value={query} aria-label={t("cargo.searchModels")} placeholder={t("cargo.searchModels")} onChange={event => { setQuery(event.target.value); setLimit(50); }} /></div>
    {error && <div className="cargo-error" role="alert">{error}<button type="button" className="cargo-text-button" onClick={() => setRetry(value => value + 1)}>{t("cargo.retry")}</button></div>}
    {archived && <div className="cargo-selection" role="status"><span>{t("cargo.archived", { name: nameOf(archived) })}</span><button className="cargo-text-button" type="button" disabled={busy} onClick={async () => {
      setBusy(true); try { const saved = await cargoApi.updateTemplate({ ...archived, active: true }); setItems(previous => [...previous.filter(model => model.id !== saved.id), saved]); setArchived(null); } catch (cause) { setError(cause instanceof Error ? cause.message : t("cargo.errors.failed")); } finally { setBusy(false); }
    }}>{t("cargo.undo")}</button></div>}
    {loading ? <p className="cargo-empty" role="status">{t("cargo.loading")}</p> : <ul className="cargo-model-list">{filtered.slice(0, limit).map(model => {
      const d = model.dimensions_mm;
      return <li key={model.id}><span className="cargo-unit-icon"><LayersIcon /></span><span className="cargo-unit-copy"><strong>{nameOf(model)}</strong><span>{[d && [d.length, d.width, d.height].every(value => value != null) ? `${[d.length, d.width, d.height].map(value => number(value!)).join(" × ")} mm` : null, model.tare_kg == null ? null : `${number(model.tare_kg)} kg`, model.reusable ? t("cargo.reusable") : null].filter(Boolean).join(" · ")}</span></span>
        {editable && <EquipmentMenu>{model.builtin ? <button type="button" onClick={() => open({ ...model, id: "", builtin: false, version: undefined })}>{t("cargo.copyModel")}</button> : <><button type="button" onClick={() => open(model)}>{t("cargo.edit")}</button><button type="button" disabled={busy} onClick={async () => {
          setBusy(true); setError(""); try { const archivedModel = await cargoApi.archiveTemplate(model); setItems(previous => previous.filter(item => item.id !== model.id)); setArchived(archivedModel); } catch (cause) { setError(cause instanceof Error ? cause.message : t("cargo.errors.failed")); } finally { setBusy(false); }
        }}>{t("cargo.archive")}</button></>}</EquipmentMenu>}
      </li>;
    })}{!filtered.length && <li className="cargo-empty">{t("cargo.noModels")}</li>}</ul>}
    {filtered.length > limit && <button type="button" className="cargo-text-button" onClick={() => setLimit(value => value + 50)}>{t("cargo.showMore")}</button>}
    {editing && <EquipmentDialog title={t(editing.id ? "cargo.editModel" : "cargo.addModel")} onClose={() => { if (!busy) setEditing(null); }}>
      <form className="cargo-form" onInvalid={event => { for (let node = (event.target as HTMLElement).parentElement; node; node = node.parentElement) if (node instanceof HTMLDetailsElement) node.open = true; }} onSubmit={async event => {
        event.preventDefault(); setBusy(true); setFormError("");
        try {
          const { id, ...fields } = editing;
          const body = { ...fields, language_labels: { ...editing.language_labels, [i18n.language.slice(0, 2)]: editing.name } };
          const saved = id ? await cargoApi.updateTemplate({ ...body, id }) : await cargoApi.createTemplate(body);
          setItems(previous => [...previous.filter(model => model.id !== saved.id), saved]); setEditing(null);
        } catch (cause) { setFormError(cause instanceof Error ? cause.message : t("cargo.errors.failed")); }
        finally { setBusy(false); }
      }}><CargoUnitFields value={editing} onChange={next => setEditing(next as PackagingTemplate)} />
        {formError && <p className="cargo-error" role="alert">{formError}</p>}
        <div className="cargo-dialog-actions"><button type="button" className="cargo-button" disabled={busy} onClick={() => setEditing(null)}>{t("cargo.cancel")}</button><button type="submit" className="cargo-button cargo-primary" disabled={busy}>{t(busy ? "cargo.saving" : "cargo.save")}</button></div>
      </form>
    </EquipmentDialog>}
  </div>;
}
