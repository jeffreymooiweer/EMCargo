import { cargoApi, type CargoUnit } from "../api/cargo";
import DeliveryActivity from "../components/DeliveryActivity";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { api, type ShipmentSummary, type User } from "../api/client";
import { deliveries, inputOf, modes, newLeg, type Allocation, type Assessment, type Delivery, type DeliveryInput, type Grant, type Leg, type ReceiptLine, type Source } from "../api/deliveries";
import { canManage } from "../permissions";
import { usePreferences } from "../settings/preferences";
import SignaturePad from "../components/SignaturePad";
import DeliveryDocumentDetails from "../components/DeliveryDocumentDetails";
import "./deliveries.css";

type Draft = DeliveryInput & { sources: Record<string, Source> };
const localDate = (value: string | null) => value ? new Date(new Date(value).getTime() - new Date(value).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "";
const iso = (value: string) => value ? new Date(value).toISOString() : null;
const initial = (): Draft => ({ name: "", legs: [newLeg()], allocations: [], sources: {} });

function allocationLabel(sources: Record<string, Source>, allocation: Allocation) {
  const source = sources[String(allocation.shipment_id)];
  const goods = source?.goods || source?.export?.goods || [];
  const line = goods.find((g, i) => String(g.id ?? g.cargo_goods_id ?? g.line_id ?? `line-${i}`) === allocation.goods_id);
  return `${source?.reference || `#${allocation.shipment_id}`} · ${line?.description || allocation.goods_id}`;
}

export default function DeliveriesPage({ user }: { user: User }) {
  const { t } = useTranslation();
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { publicSettings } = usePreferences();
  const [items, setItems] = useState<Pick<Delivery, "id" | "name" | "status" | "version">[]>([]);
  const [canPlan, setCanPlan] = useState(false);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [record, setRecord] = useState<Delivery | null>(null);
  const [draft, setDraft] = useState<Draft>(initial);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [documentDirty, setDocumentDirty] = useState(false);
  const [notice, setNotice] = useState("");
  const [shipments, setShipments] = useState<ShipmentSummary[]>([]);
  const [loadUnits, setLoadUnits] = useState<CargoUnit[]>([]);
  useEffect(() => { let active = true; if (publicSettings?.history_enabled && !["operator", "recipient", "external"].includes(user.role)) cargoApi.reusableUnits().then(units => { if (active) setLoadUnits(units.filter(unit => unit.kind === "ctu")); }).catch(() => {}); return () => { active = false; }; }, [publicSettings?.history_enabled, user.role]);
  const [sourceQuery, setSourceQuery] = useState("");
  const [shipmentId, setShipmentId] = useState("");
  const generation = useRef(0);
  const routeId = useRef(id); routeId.current = id;
  const creating = id === "new";
  const detail = !!id;
  const scoped = user.execution_only || ["operator", "recipient", "external"].includes(user.role);
  const editable = creating || !!record?.can_plan;
  const allocationEditable = editable && !record?.followup;
  const [tab, setTab] = useState("planning");
  const tabs = ["planning", "checks", "execution", "documents", "access", "history"];
  const keys: Record<string, string> = { planning: "goods", checks: "checks", execution: "execution", documents: "documents", access: "access", history: "history" };
  const accept = (value: Delivery) => { if (routeId.current && routeId.current !== "new" && value.id !== routeId.current) return; setRecord(value); setDraft({ ...inputOf(value), legs: value.legs, sources: Object.fromEntries(Object.entries(value.sources).map(([sid, source]) => [sid, { ...source, packing_units: value.packing_units?.[sid] }])) }); };
  async function run(work: () => Promise<void>) {
    if (busy) return;
    const current = generation.current;
    setBusy(true); setFailure(""); setNotice("");
    try { await work(); } catch (error) { if (generation.current === current) setFailure(error instanceof Error ? error.message : String(error)); }
    finally { if (generation.current === current) setBusy(false); }
  }
  async function attach(target: Draft, ids: number[]) {
    const next = structuredClone(target);
    for (const sid of ids) {
      if (next.sources[String(sid)]) continue;
      const [source, balance] = await Promise.all([deliveries.source(sid), deliveries.balances(sid)]);
      const available = new Map(balance.goods.map(g => [g.id, g.available]));
      next.sources[String(sid)] = { reference: source.reference, packing_units: source.packing_units, goods: source.goods.map(g => ({ ...g, id: g.delivery_goods_id })) };
      next.allocations.push(...source.goods.filter(g => Number(available.get(g.delivery_goods_id!) || "0") > 0).map(g => ({ id: crypto.randomUUID(), shipment_id: sid, goods_id: g.delivery_goods_id!, quantity: available.get(g.delivery_goods_id!)!, leg_ids: next.legs[0] ? [next.legs[0].id] : [], unit_ids: source.packing_units?.filter(u => u.available !== false && g.delivery_goods_id! in u.goods).map(u => u.id) })));
      if (!next.name) next.name = source.reference;
    }
    return next;
  }
  useEffect(() => {
    const current = ++generation.current;
    setFailure(""); setNotice(""); setRecord(null); setTab("planning");
    if (!publicSettings?.history_enabled) return;
    setBusy(true);
    const task = creating ? attach(initial(), (params.get("shipments") || "").split(",").map(Number).filter(n => n > 0)).then(value => { if (generation.current === current) setDraft(value); })
      : id ? deliveries.get(id).then(value => { if (generation.current === current) { accept(value); if (!value.can_plan) setTab("execution"); } })
      : deliveries.list(`?q=${encodeURIComponent(query)}&page=${page}`).then(result => { if (generation.current === current) { setItems(result.items); setCanPlan(result.can_plan); setTotal(result.total); } });
    task.catch(error => { if (generation.current === current) setFailure(error.message); }).finally(() => { if (generation.current === current) setBusy(false); });
    return () => { generation.current++; };
  }, [id, publicSettings?.history_enabled, query, page]);
  useEffect(() => {
    if (!editable || !detail || !publicSettings?.history_enabled) return;
    let cancelled = false;
    api.shipments({ q: sourceQuery, per_page: 100 }).then(result => { if (!cancelled) setShipments(result.items.filter(s => !s.is_draft)); }).catch(error => { if (!cancelled) setFailure(error.message); });
    return () => { cancelled = true; };
  }, [sourceQuery, editable, detail, publicSettings?.history_enabled]);
  const changeLeg = (legId: string, update: Partial<Leg>) => setDraft(previous => ({ ...previous, legs: previous.legs.map(l => l.id === legId ? { ...l, ...update } : l) }));
  const changeAllocation = (allocationId: string, update: Partial<Allocation>) => setDraft(previous => ({ ...previous, allocations: previous.allocations.map(a => a.id === allocationId ? { ...a, ...update } : a) }));
  function toggleUnit(sid: string, uid: string, checked: boolean) {
    const groups = draft.sources[sid].packing_units || [];
    const group = groups.find(u => u.id === uid)!;
    if (draft.allocations.some(a => String(a.shipment_id) === sid && !/^\d+(?:\.\d{0,6})?$/.test(a.quantity))) { setFailure(t("errors.delivery.quantity")); return; }
    const micro = (value: string) => { const [whole, fraction = ""] = value.split("."); return BigInt(whole || "0") * 1000000n + BigInt(fraction.padEnd(6, "0").slice(0, 6)); };
    const decimal = (value: bigint) => `${value / 1000000n}.${String(value % 1000000n).padStart(6, "0")}`.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "");
    setDraft(previous => {
      const allocations = [...previous.allocations];
      for (const [gid, quantity] of Object.entries(group.goods)) {
        const index = allocations.findIndex(a => String(a.shipment_id) === sid && a.goods_id === gid);
        const old = allocations[index];
        const ids = old?.unit_ids ?? groups.filter(u => gid in u.goods).map(u => u.id);
        const included = old && ids.includes(uid);
        if (!!included === checked) continue;
        const amount = (old ? micro(old.quantity) : 0n) + (checked ? micro(quantity) : -micro(quantity));
        if (amount <= 0n) { if (index >= 0) allocations.splice(index, 1); continue; }
        const allocation = { ...(old || { id: crypto.randomUUID(), shipment_id: Number(sid), goods_id: gid, leg_ids: previous.legs[0] ? [previous.legs[0].id] : [] }), quantity: decimal(amount), unit_ids: checked ? [...(old ? ids : []), uid] : ids.filter(id => id !== uid) };
        if (index < 0) allocations.push(allocation); else allocations[index] = allocation;
      }
      return { ...previous, allocations };
    });
  }
  const goodsLabel = (a: Allocation) => allocationLabel(draft.sources, a);
  const dirty = !!record && JSON.stringify(inputOf(draft)) !== JSON.stringify(inputOf(record));
  useEffect(() => {
    if (!dirty && !documentDirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    const leave = (event: MouseEvent) => {
      const anchor = (event.target as Element).closest?.("a[href]") as HTMLAnchorElement | null;
      if (anchor && anchor.origin === location.origin && !anchor.pathname.startsWith("/api/") && anchor.href !== location.href && !window.confirm(t("deliveries.discardChanges"))) { event.preventDefault(); event.stopImmediatePropagation(); }
    };
    window.addEventListener("beforeunload", warn); document.addEventListener("click", leave, true);
    return () => { window.removeEventListener("beforeunload", warn); document.removeEventListener("click", leave, true); };
  }, [dirty, documentDirty, t]);

  return <div className="deliveries-page page-enter">
    <header className="page-heading"><div><p className="eyebrow">EMCargo</p><h2>{creating ? draft.name || t("deliveries.new") : record?.name || t("deliveries.title")}</h2><p>{t(scoped ? "deliveries.scopedIntro" : "deliveries.intro")}</p></div>
      <div className="delivery-actions">{detail ? <Link className="action-secondary" to="/deliveries">{t("deliveries.title")}</Link> : canPlan && <Link className="action-primary" to="/deliveries/new">+ {t("deliveries.new")}</Link>}
      {!detail && !["operator", "recipient", "external"].includes(user.role) && <Link className="action-secondary" to="/trips">{t("deliveries.legacy")}</Link>}</div>
    </header>
    {failure && <div className="delivery-error" role="alert">{failure}</div>}
    {notice && <p role="status">{notice}</p>}
    {(dirty || documentDirty) && <p className="delivery-callout" role="status">{t("deliveries.unsaved")}</p>}
    {!detail && canPlan && <details className="surface delivery-panel"><summary>{t("deliveries.operations")}</summary><DeliveryActivity /></details>}
    {!detail && canPlan && <details className="surface delivery-panel"><summary>{t("deliveries.importArchive")}</summary><label>{t("deliveries.importArchive")}<input type="file" accept=".zip,.json" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) run(async () => { const imported = await deliveries.import(file); navigate(`/deliveries/${imported.id}`); }); e.target.value = ""; }} /></label><p>{t("deliveries.importHint")}</p></details>}
    {record?.legacy_consignments && <aside className="delivery-callout"><p>{t("deliveries.legacyHint")}</p><ul>{record.legacy_consignments.map((c, i) => <li key={i}>{c.name}</li>)}</ul></aside>}
    {!publicSettings?.history_enabled ? <section className="surface delivery-panel"><p>{t("deliveries.noHistory")}</p></section> : !detail ? <>
      <label className="delivery-search">{t("deliveries.name")}<input value={query} onChange={e => { setPage(1); setQuery(e.target.value); }} /></label>
      {busy && <p role="status">{t("wizard.loading")}</p>}
      <div className="delivery-list">{items.map(item => <Link key={item.id} to={`/deliveries/${item.id}`} className="surface delivery-list-card"><strong>{item.name}</strong><span className={`delivery-status state-${item.status}`}>{t(`deliveries.status.${item.status}`)}</span><span aria-hidden="true">→</span></Link>)}</div>
      {!busy && !items.length && <p>{t("deliveries.empty")}</p>}
      {total > 25 && <div className="delivery-actions"><button disabled={page === 1 || busy} onClick={() => setPage(p => p - 1)}>←</button><span>{page} / {Math.ceil(total / 25)}</span><button disabled={page * 25 >= total || busy} onClick={() => setPage(p => p + 1)}>→</button></div>}
    </> : !creating && !record ? <p role="status">{busy ? t("wizard.loading") : ""}</p> : <>
      {record && <div className="delivery-actions"><span className={`delivery-status state-${record.status}`}>{t(`deliveries.status.${record.status}`)}</span><a className="action-secondary" href={`/api/deliveries/v1/${record.id}/export`}>{t("deliveries.export")}</a><button type="button" className="action-secondary" disabled={busy} onClick={() => { if ((!dirty && !documentDirty) || window.confirm(t("deliveries.discardChanges"))) run(async () => accept(await deliveries.get(record.id))); }}>{t("deliveries.reload")}</button></div>}
      <nav className="delivery-tabs" aria-label={t("deliveries.title")}>{tabs.filter(key => !creating || key === "planning").filter(key => canManage(user) || key !== "access").filter(key => editable || !["planning", "checks"].includes(key)).map(key => <button key={key} type="button" aria-current={tab === key ? "page" : undefined} onClick={() => { if (!documentDirty || window.confirm(t("deliveries.discardChanges"))) setTab(key); }}>{t(`deliveries.${keys[key]}`)}</button>)}</nav>
      {tab === "planning" && <section className="surface delivery-panel">
        <form onSubmit={e => { e.preventDefault(); run(async () => { const saved = creating ? await deliveries.create(inputOf(draft)) : await deliveries.save(record!.id, inputOf(draft)); accept(saved); setNotice(t("deliveries.saved")); if (creating) navigate(`/deliveries/${saved.id}`, { replace: true }); }); }}>
          <label>{t("deliveries.name")}<input required maxLength={120} value={draft.name} disabled={busy || !editable} onChange={e => setDraft({ ...draft, name: e.target.value })} /></label>
          <div className="delivery-leg-grid">{draft.legs.map((part, index) => <fieldset key={part.id} disabled={busy || !editable || !!part.status && part.status !== "draft"} className="delivery-leg-card"><legend>{t("deliveries.leg")} {index + 1}</legend>
            <label>{t("deliveries.mode")}<select value={part.mode} onChange={e => changeLeg(part.id, { mode: e.target.value as Leg["mode"] })}>{modes.map(mode => <option key={mode} value={mode}>{t(`deliveries.modes.${mode}`)}</option>)}</select></label>
            {(["origin", "destination", "carrier", "vehicle", "reference"] as const).map(key => <label key={key}>{t(`deliveries.${key}`)}<input value={part[key]} maxLength={key === "origin" || key === "destination" ? 500 : 120} onChange={e => changeLeg(part.id, { [key]: e.target.value })} /></label>)}
            <label>{t("deliveries.sharedLoadUnit")}<select value={part.load_unit_id || ""} onChange={e => changeLeg(part.id, { load_unit_id: e.target.value || null })}><option value="">—</option>{loadUnits.map(unit => <option key={unit.id} value={unit.id}>{unit.code} · {unit.name}</option>)}</select></label>
            <label>{t("deliveries.start")}<input type="datetime-local" value={localDate(part.planned_start)} onChange={e => changeLeg(part.id, { planned_start: iso(e.target.value) })} /></label>
            <label>{t("deliveries.maxMass")}<input type="number" min="0.000001" step="any" value={part.max_mass_tonnes || ""} onChange={e => changeLeg(part.id, { max_mass_tonnes: e.target.value || null })} /></label>
            <label>{t("deliveries.end")}<input type="datetime-local" value={localDate(part.planned_end)} onChange={e => changeLeg(part.id, { planned_end: iso(e.target.value) })} /></label>
            <button type="button" className="action-secondary" disabled={!allocationEditable} onClick={() => setDraft({ ...draft, legs: draft.legs.filter(l => l.id !== part.id), allocations: draft.allocations.map(a => ({ ...a, leg_ids: a.leg_ids.filter(l => l !== part.id) })) })}>{t("deliveries.remove")}</button>
          </fieldset>)}</div>
          {allocationEditable && <button type="button" className="action-secondary" disabled={busy} onClick={() => setDraft({ ...draft, legs: [...draft.legs, newLeg()] })}>+ {t("deliveries.addLeg")}</button>}
          <h3>{t("deliveries.goods")}</h3><p>{t("deliveries.sourceHint")}</p>{draft.legs.length > 1 && <p>{t("deliveries.onwardHint")}</p>}
          {allocationEditable && <div className="delivery-source-picker"><label>{t("deliveries.shipmentId")}<input value={sourceQuery} onChange={e => setSourceQuery(e.target.value)} /></label><label>{t("deliveries.select")}<select value={shipmentId} onChange={e => setShipmentId(e.target.value)}><option value="">—</option>{shipments.filter(s => !draft.sources[String(s.id)]).map(s => <option key={s.id} value={s.id}>#{s.id} {s.reference} · {s.consignee_name}</option>)}</select></label><button type="button" className="action-secondary" disabled={busy || !shipmentId} onClick={() => run(async () => { setDraft(await attach(draft, [Number(shipmentId)])); setShipmentId(""); })}>+ {t("deliveries.addShipment")}</button></div>}
          {record?.followup && <p className="delivery-callout">{t("deliveries.followupPlanningHint")}</p>}
          {Object.entries(draft.sources).map(([sid, source]) => !!source.packing_units?.length && <fieldset className="delivery-leg-card" key={sid} disabled={busy || !allocationEditable || draft.allocations.some(a => String(a.shipment_id) === sid && a.leg_ids.some(lid => draft.legs.find(p => p.id === lid)?.status !== "draft"))}>
            <legend>{source.reference} · {t("deliveries.packingUnits")}</legend><p>{t("deliveries.packingUnitsHint")}</p>
            {source.packing_units.map(unit => <label className="delivery-file-choice" key={unit.id}><input type="checkbox" disabled={unit.available === false} checked={draft.allocations.some(a => String(a.shipment_id) === sid && (a.unit_ids ? a.unit_ids.includes(unit.id) : a.goods_id in unit.goods))} onChange={e => toggleUnit(sid, unit.id, e.target.checked)} />{unit.code} · {unit.name}</label>)}
          </fieldset>)}
          <div className="delivery-cargo">{draft.allocations.map(a => <div key={a.id} className="delivery-allocation"><strong>{goodsLabel(a)}</strong><label>{t("deliveries.quantity")}<input aria-label={`${t("deliveries.quantity")} ${goodsLabel(a)}`} inputMode="decimal" value={a.quantity} disabled={busy || !allocationEditable || a.leg_ids.some(l => draft.legs.find(p => p.id === l)?.status !== "draft")} onChange={e => changeAllocation(a.id, { quantity: e.target.value })} /></label><div className="delivery-itinerary">{draft.legs.map((part, i) => <label key={part.id}><input type="checkbox" checked={a.leg_ids.includes(part.id)} disabled={busy || !allocationEditable || a.leg_ids.some(lid => draft.legs.find(p => p.id === lid)?.status !== "draft")} onChange={e => changeAllocation(a.id, { leg_ids: e.target.checked ? draft.legs.map(l => l.id).filter(lid => a.leg_ids.includes(lid) || lid === part.id) : a.leg_ids.filter(l => l !== part.id), leg_quantities: {} })} />{i + 1}. {t(`deliveries.modes.${part.mode}`)}</label>)}</div>{a.leg_ids.slice(1).map((lid, index) => <label className="delivery-leg-quantity" key={lid}>{t("deliveries.onwardQuantity", { number: index + 2 })}<input inputMode="decimal" value={a.leg_quantities?.[lid] ?? a.quantity} disabled={busy || !allocationEditable || draft.legs.find(p => p.id === lid)?.status !== "draft"} onChange={e => changeAllocation(a.id, { leg_quantities: { ...a.leg_quantities, [lid]: e.target.value } })} /></label>)}<button type="button" className="action-secondary" disabled={busy || !allocationEditable || a.leg_ids.some(l => draft.legs.find(p => p.id === l)?.status !== "draft")} onClick={() => setDraft({ ...draft, allocations: draft.allocations.filter(item => item.id !== a.id) })}>{t("deliveries.remove")}</button></div>)}</div>
          {editable && <button className="action-primary" disabled={busy || !draft.name}>{busy ? t("deliveries.saving") : t("deliveries.save")}</button>}
        </form>
      </section>}
      {record && tab !== "planning" && <DeliveryWork key={record.id} record={record} tab={tab} user={user} documentDirty={documentDirty} setDocumentDirty={setDocumentDirty} busy={busy || dirty} accept={accept} run={run} notify={setNotice} />}
    </>}
  </div>;
}

function DeliveryWork({ record, tab, user, busy: externalBusy, documentDirty, setDocumentDirty, accept, run, notify }: { record: Delivery; tab: string; user: User; busy: boolean; documentDirty: boolean; setDocumentDirty: (dirty: boolean) => void; accept: (d: Delivery) => void; run: (work: () => Promise<void>) => Promise<void>; notify: (message: string) => void }) {
  const { t, i18n } = useTranslation();
  const busy = externalBusy || documentDirty;
  const discardDetails = () => !documentDirty || window.confirm(t("deliveries.discardChanges"));
  const [legId, setLegId] = useState(record.legs[0]?.id || "");
  const part = record.legs.find(l => l.id === legId);
  const [reason, setReason] = useState("");
  const [result, setResult] = useState<Assessment | null>(null);
  const [recipient, setRecipient] = useState("");
  const [occurred, setOccurred] = useState(localDate(new Date().toISOString()));
  const [lines, setLines] = useState<Record<string, ReceiptLine>>({});
  const [signature, setSignature] = useState<string | null>(null);
  const [unloadIds, setUnloadIds] = useState<string[]>([]);
  const [proofIds, setProofIds] = useState<string[]>([]);
  const [fileIds, setFileIds] = useState<string[]>([]);
  const [mailTo, setMailTo] = useState("");
  const [mailMessage, setMailMessage] = useState("");
  const [reviewDocs, setReviewDocs] = useState<string[]>([]);
  const [accounts, setAccounts] = useState<User[]>([]);
  const [scopeIds, setScopeIds] = useState<string[]>([]);
  const [contractReference, setContractReference] = useState("");
  const [docKey, setDocKey] = useState("cmr");
  const [docOptions, setDocOptions] = useState<{ key: string; label: Record<string, string> }[]>([]);
  const [shipmentId, setShipmentId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileKind, setFileKind] = useState("proof");
  const [email, setEmail] = useState("");
  const [userId, setUserId] = useState("");
  const [grantShipments, setGrantShipments] = useState<number[]>([]);
  const [grantRole, setGrantRole] = useState("operator");
  const [expires, setExpires] = useState(localDate(new Date(Date.now() + 7 * 86400000).toISOString()));
  const [grants, setGrants] = useState<Grant[]>([]);
  const [corrects, setCorrects] = useState("");
  const [resolution, setResolution] = useState("accept");
  const requestId = useRef(crypto.randomUUID());
  const requestKind = useRef("");
  const allocations = record.allocations.filter(a => a.leg_ids.includes(legId)).map(a => ({ ...a, quantity: a.leg_quantities?.[legId] ?? a.quantity }));
  const shipmentIds = [...new Set(allocations.map(a => a.shipment_id))];
  useEffect(() => { setResult(null); setLines({}); setUnloadIds([]); setGrantShipments([]); setScopeIds([]); setShipmentId(previous => shipmentIds.includes(Number(previous)) ? previous : ""); setFileIds([]); setReviewDocs([]); setProofIds([]); setSignature(null); requestId.current = crypto.randomUUID(); }, [legId, record.version]);
  useEffect(() => { if (tab === "documents" && record.can_plan) api.documentsRegistry().then(registry => setDocOptions(registry.documents.filter(doc => registry.modalities.find(mode => mode.key === part?.mode)?.documents.includes(doc.key)) as unknown as typeof docOptions)).catch(() => setDocOptions([])); }, [tab, record.can_plan, part?.mode]);
  useEffect(() => { if (tab === "access" && canManage(user)) run(async () => { setGrants(await deliveries.grants(record.id)); setAccounts(await api.listUsers()); }); }, [tab]);
  useEffect(() => { if (docOptions.length && !docOptions.some(d => d.key === docKey)) setDocKey(docOptions[0].key); }, [docOptions]);
  const formLine = (a: Allocation): ReceiptLine => lines[a.id] || { allocation_id: a.id, quantity: "", damaged: "0", refused: "0" };
  const can = (role: string) => record.can_plan || record.assignments.some(a => a.role === role && a.leg_id === legId);
  function submitEvent(kind: string) {
    if (requestKind.current !== kind) { requestId.current = crypto.randomUUID(); requestKind.current = kind; }
    run(async () => {
      const selected = allocations.map(formLine).filter(l => l.quantity !== "");
      accept(await deliveries.event(record.id, legId, { version: record.version, request_id: requestId.current, kind, signature_image: signature, file_ids: proofIds, recipient, occurred_at: iso(occurred), lines: selected, reason, corrects: kind === "correction" ? corrects : null, resolution: kind === "resolution" ? resolution : null }));
      requestId.current = crypto.randomUUID(); notify(t("deliveries.saved"));
    });
  }
  if (tab === "history") return <section className="surface delivery-panel"><h3>{t("deliveries.history")}</h3>
    {record.followup && <Link to={`/deliveries/${record.followup.parent_id}`}>{t("deliveries.originalDelivery")}</Link>}
    <ol className="delivery-history">{record.events.map(e => <li key={e.request_id}>
      {record.legs.filter(l => l.id === e.leg_id).map(l => <p key={l.id}>{t("deliveries.leg")} {record.legs.indexOf(l) + 1} · {t(`deliveries.modes.${l.mode}`)} · {l.origin} → {l.destination}</p>)}
      <strong>{t(`deliveries.${e.kind}`)}</strong> · {new Date(e.occurred_at).toLocaleString()} · {e.recipient}<p>{e.reason}</p>
      {e.unit_ids && <p>{t("deliveries.packingUnits")}: {e.unit_ids.map(id => record.cargo_units?.[e.leg_id]?.find(u => u.id === id)?.code || id).join(", ")}</p>}
      {e.kind !== "unload" && e.lines.map(l => { const allocation = record.allocations.find(a => a.id === l.allocation_id); return <p key={l.allocation_id}>
        {allocation && <strong>{allocationLabel(record.sources, allocation)} · </strong>}
        {t(e.kind === "load" || e.corrected_kind === "load" ? "deliveries.loaded" : "deliveries.quantity")}: {l.quantity}
        {e.kind !== "load" && <> · {t("deliveries.damaged")}: {l.damaged} · {t("deliveries.refused")}: {l.refused}</>}
      </p>; })}
      {e.followup_id && <p><Link to={`/deliveries/${e.followup_id}`}>{t(e.resolution === "return" ? "deliveries.returnDelivery" : "deliveries.redeliveryDelivery")}</Link> · {t(e.followup_complete ? "deliveries.status.completed" : "deliveries.followupPending")}</p>}
      {e.file_ids?.map(id => { const file = record.files.find(f => f.id === id); return file && <a key={id} href={`/api/deliveries/v1/${record.id}/files/${id}`}>{file.filename}</a>; })}
    </li>)}</ol>
  </section>;

  return <section className="surface delivery-panel"><label>{t("deliveries.leg")}<select value={legId} onChange={e => { if (discardDetails()) setLegId(e.target.value); }}>{record.legs.map((l, i) => <option key={l.id} value={l.id}>{i + 1}. {t(`deliveries.modes.${l.mode}`)} · {l.origin} → {l.destination}</option>)}</select></label>
    {part && <><span className={`delivery-status state-${part.status}`}>{t(`deliveries.status.${part.status}`)}</span>
    {tab === "checks" && <>
      {record.can_review && part.status === "planned" && record.files.filter(f => f.leg_id === legId && f.kind === "external").map(f => <label key={f.id} className="delivery-file-choice"><input type="checkbox" checked={reviewDocs.includes(f.id)} onChange={e => setReviewDocs(ids => e.target.checked ? [...ids, f.id] : ids.filter(id => id !== f.id))} /><a href={`/api/deliveries/v1/${record.id}/files/${f.id}`}>{f.filename}</a>{t("deliveries.reviewedAttachment")}</label>)}
      <label>{t("deliveries.reason")}<textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={4000} /></label>
      <div className="delivery-actions"><button className="action-secondary" disabled={busy} onClick={() => run(async () => setResult(await deliveries.assessment(record.id, legId, i18n.language)))}>{t("deliveries.assess")}</button>
        {record.can_review && part.status === "planned" && <button className="action-secondary" disabled={busy || reason.trim().length < 10} onClick={() => run(async () => accept(await deliveries.review(record.id, legId, record.version, reason, reviewDocs, i18n.language)))}>{t("deliveries.review")}</button>}
        {record.can_plan && ({ draft: ["plan", "cancel"], planned: ["release", "unplan", "cancel"], released: ["reopen", "cancel"], in_progress: [], completed: ["close"], closed: [], cancelled: [], partial: [] }[part.status || "draft"]).map(action => <button key={action} className={action === "release" ? "action-primary" : "action-secondary"} disabled={busy} onClick={() => run(async () => accept(await deliveries.action(record.id, legId, record.version, action, reason, i18n.language)))}>{t(`deliveries.${action}`)}</button>)}
      </div>
      {(result || part.assessment) && <div className={(result || part.assessment)!.blocked ? "delivery-error" : "delivery-callout"}><p>{t((result || part.assessment)!.blocked ? "deliveries.blocked" : (result || part.assessment)!.manual_required ? "deliveries.partialCoverage" : "deliveries.ordinary")}</p><AssessmentDetails result={(result || part.assessment)!} /></div>}
      {part.review && <blockquote><p>{part.review.reason}</p><time>{new Date(part.review.at).toLocaleString()}</time></blockquote>}
    </>}
    {tab === "execution" && <><p className="delivery-callout">{t("deliveries.online")}</p><div className="delivery-form-grid"><label>{t("deliveries.recipient")}<input value={recipient} onChange={e => setRecipient(e.target.value)} maxLength={255} /></label><label>{t("deliveries.occurred")}<input type="datetime-local" value={occurred} onChange={e => setOccurred(e.target.value)} /></label></div>
      {allocations.map(a => <fieldset className="delivery-receipt" key={a.id}><legend>{allocationLabel(record.sources, a)} ({a.quantity})</legend><p className="delivery-receipt-total">{t("deliveries.received")}: {record.receipt_totals?.[legId]?.[a.id]?.quantity || "0"} / {a.quantity}</p>{(["quantity", "damaged", "refused"] as const).map(key => <label key={key}>{t(`deliveries.${key}`)}<input inputMode="decimal" value={formLine(a)[key]} onChange={e => { requestId.current = crypto.randomUUID(); setLines({ ...lines, [a.id]: { ...formLine(a), [key]: e.target.value } }); }} /></label>)}</fieldset>)}
      <SignaturePad key={`${legId}-${record.version}`} title={t("deliveries.signature")} value={signature} onChange={value => { requestId.current = crypto.randomUUID(); setSignature(value); }} />
      {record.files.filter(f => f.leg_id === legId && f.kind === "proof").map(f => <label className="delivery-file-choice" key={f.id}><input type="checkbox" checked={proofIds.includes(f.id)} onChange={e => { requestId.current = crypto.randomUUID(); setProofIds(ids => e.target.checked ? [...ids, f.id] : ids.filter(id => id !== f.id)); }} />{f.filename}</label>)}
      <label>{t("deliveries.reason")}<textarea value={reason} onChange={e => setReason(e.target.value)} /></label>
      {record.unpack_legs?.includes(legId) && <div className="delivery-callout"><p>{t("deliveries.unpackHint")}</p><button type="button" className="action-secondary" disabled={busy || !recipient || !occurred || reason.trim().length < 10} onClick={() => submitEvent("unpack")}>{t("deliveries.unpack")}</button></div>}
      <div className="delivery-actions">{can("operator") && <button className="action-primary" disabled={busy || !recipient || !occurred || !["released", "in_progress"].includes(part.status || "")} onClick={() => submitEvent("load")}>{t("deliveries.load")}</button>}{can("recipient") && <button className="action-primary" disabled={busy || !recipient || !occurred || !["released", "in_progress"].includes(part.status || "")} onClick={() => submitEvent("receipt")}>{t("deliveries.receipt")}</button>}</div>
      {can("operator") && !!record.cargo_units?.[legId]?.length && <fieldset className="delivery-leg-card"><legend>{t("deliveries.unload")}</legend><p>{t("deliveries.unloadHint")}</p>
        {record.cargo_units[legId].filter(u => u.released).map(unit => <p key={unit.id}>{unit.code} · {t("deliveries.unitAvailable")}</p>)}
        {record.cargo_units[legId].filter(u => !u.released).map(unit => <label className="delivery-file-choice" key={unit.id}><input type="checkbox" checked={unloadIds.includes(unit.id)} onChange={e => { requestId.current = crypto.randomUUID(); setUnloadIds(ids => e.target.checked ? [...ids, unit.id] : ids.filter(id => id !== unit.id)); }} />{unit.code} · {unit.name}</label>)}
        <button type="button" className="action-secondary" disabled={busy || !unloadIds.length || !recipient || !occurred || reason.trim().length < 10 || !["in_progress", "completed", "closed"].includes(part.status || "")} onClick={() => run(async () => { if (requestKind.current !== "unload") { requestId.current = crypto.randomUUID(); requestKind.current = "unload"; } accept(await deliveries.unload(record.id, legId, { version: record.version, request_id: requestId.current, unit_ids: unloadIds, recipient, occurred_at: iso(occurred), reason })); notify(t("deliveries.saved")); })}>{t("deliveries.unload")}</button>
      </fieldset>}
      {record.can_plan && <details><summary>{t("deliveries.correction")} / {t("deliveries.resolution")}</summary><label>{t("deliveries.select")}<select value={corrects} onChange={e => setCorrects(e.target.value)}><option value="">—</option>{record.events.filter(e => e.leg_id === legId && !["resolution", "unload", "unpack"].includes(e.kind)).map(e => <option key={e.request_id} value={e.request_id}>{t(`deliveries.${e.kind}`)} · {new Date(e.occurred_at).toLocaleString()} · {e.recipient}</option>)}</select></label><button className="action-secondary" disabled={busy || !corrects || !reason || !recipient} onClick={() => submitEvent("correction")}>{t("deliveries.correction")}</button><label>{t("deliveries.resolution")}<select value={resolution} onChange={e => setResolution(e.target.value)}>{["accept", "redelivery", "return"].map(value => <option key={value} value={value}>{t(`deliveries.${value}`)}</option>)}</select></label><button className="action-secondary" disabled={busy || !reason || !recipient} onClick={() => submitEvent("resolution")}>{t("deliveries.resolution")}</button></details>}
    </>}
    {tab === "documents" && <><label>{t("deliveries.shipmentId")}<select value={shipmentId} onChange={e => { if (discardDetails()) setShipmentId(e.target.value); }}><option value="">—</option>{shipmentIds.map(sid => <option key={sid} value={sid}>{record.sources[String(sid)]?.reference || sid}</option>)}</select></label>
      {record.can_plan && <div className="delivery-form-grid"><label>{t("deliveries.documentKey")}<select value={docKey} onChange={e => { if (discardDetails()) setDocKey(e.target.value); }}>{docOptions.map(doc => <option key={doc.key} value={doc.key}>{doc.label?.[i18n.language] || doc.key}</option>)}</select></label><button className="action-primary" disabled={busy || !shipmentId || !["released", "in_progress"].includes(part.status || "")} onClick={() => run(async () => accept(await deliveries.issue(record.id, legId, { version: record.version, shipment_id: Number(shipmentId), document_key: docKey, leg_ids: [legId, ...scopeIds], contract_reference: contractReference, language: i18n.language.slice(0, 2) }))) }>{t("deliveries.issue")}</button></div>}
      {record.can_plan && shipmentId && <fieldset className="delivery-leg-card"><legend>{t("deliveries.documentScope")}</legend><p>{t("deliveries.documentScopeHint")}</p>
        {record.legs.filter(l => l.id !== legId && l.mode === part.mode && allocations.some(a => a.shipment_id === Number(shipmentId) && a.leg_ids.indexOf(l.id) > a.leg_ids.indexOf(legId))).map((l) => <label className="delivery-file-choice" key={l.id}><input type="checkbox" checked={scopeIds.includes(l.id)} onChange={e => setScopeIds(ids => e.target.checked ? [...ids, l.id] : ids.filter(id => id !== l.id))} />{l.origin} → {l.destination}</label>)}
        {scopeIds.length > 0 && <label>{t("deliveries.contractReference")}<input value={contractReference} maxLength={120} onChange={e => setContractReference(e.target.value)} /></label>}
      </fieldset>}
      {record.can_plan && shipmentId && <DeliveryDocumentDetails key={`${legId}-${shipmentId}-${docKey}`} record={record} part={part} shipmentId={shipmentId} documentKey={docKey} busy={externalBusy} accept={accept} run={run} onDirtyChange={setDocumentDirty} />}
      <div className="delivery-form-grid"><label>{t("deliveries.upload")}<select value={fileKind} onChange={e => setFileKind(e.target.value)}><option value="proof">{t("deliveries.proof")}</option>{record.can_plan && <option value="external">{t("deliveries.external")}</option>}</select><input type="file" accept="application/pdf,image/jpeg,image/png" onChange={e => setFile(e.target.files?.[0] || null)} /></label><button className="action-secondary" disabled={busy || !file || !shipmentId} onClick={() => run(async () => { accept(await deliveries.upload(record.id, legId, record.version, fileKind, [Number(shipmentId)], file!)); setFile(null); })}>{t("deliveries.upload")}</button></div>
      <ul className="delivery-files">{record.files.filter(f => f.leg_id === legId).map(f => <li key={f.id}>{f.current && <input type="checkbox" aria-label={`${t("deliveries.select")} ${f.filename}`} checked={fileIds.includes(f.id)} onChange={e => setFileIds(ids => e.target.checked ? [...ids, f.id] : ids.filter(id => id !== f.id))} />}<a href={`/api/deliveries/v1/${record.id}/files/${f.id}`}>{f.filename}</a><span>{t(f.current ? "deliveries.current" : "deliveries.superseded")}</span></li>)}</ul>
    </>}
    {tab === "documents" && <div className="delivery-form-grid"><button type="button" className="action-secondary" disabled={busy || !fileIds.length} onClick={() => run(async () => { await deliveries.bundle(record.id, record.version, fileIds); })}>{t("deliveries.bundle")}</button>{record.can_plan && <><label>{t("deliveries.email")}<input type="email" value={mailTo} onChange={e => setMailTo(e.target.value)} /></label><label>{t("deliveries.mailMessage")}<textarea value={mailMessage} maxLength={4000} onChange={e => setMailMessage(e.target.value)} /></label><button type="button" className="action-primary" disabled={busy || !fileIds.length || !mailTo} onClick={() => run(async () => { await deliveries.mail(record.id, { version: record.version, file_ids: fileIds, to: [mailTo], message: mailMessage, language: i18n.language.slice(0, 2) }); notify(t("deliveries.mailSent")); })}>{t("deliveries.mail")}</button></>}</div>}
    {tab === "access" && canManage(user) && <><div className="delivery-form-grid"><label>{t("deliveries.userId")}<select value={userId} onChange={e => setUserId(e.target.value)}><option value="">—</option>{accounts.filter(account => account.active !== false).map(account => <option key={account.id} value={account.id}>{account.username} · {account.email}</option>)}</select></label><label>{t("deliveries.email")}<input type="email" disabled={!!userId} value={email} onChange={e => setEmail(e.target.value)} /></label><label>{t("users.role")}<select value={grantRole} onChange={e => setGrantRole(e.target.value)}>{["operator", "recipient"].map(role => <option key={role} value={role}>{t(`deliveries.roles.${role}`)}</option>)}</select></label><label>{t("deliveries.expires")}<input type="datetime-local" value={expires} onChange={e => setExpires(e.target.value)} /></label><fieldset><legend>{t("deliveries.goods")}</legend>{shipmentIds.map(sid => <label className="delivery-file-choice" key={sid}><input type="checkbox" checked={grantShipments.includes(sid)} onChange={e => setGrantShipments(ids => e.target.checked ? [...ids, sid] : ids.filter(id => id !== sid))} />{record.sources[String(sid)]?.reference || sid}</label>)}</fieldset></div><button className="action-primary" disabled={busy || !grantShipments.length || (!email && !userId)} onClick={() => run(async () => { await deliveries.invite(record.id, { user_id: userId ? Number(userId) : null, email, role: grantRole, leg_id: legId, shipment_ids: grantShipments, expires_at: iso(expires) }); setGrants(await deliveries.grants(record.id)); notify(t("deliveries.assignmentSaved")); })}>{t("deliveries.invite")}</button><ul className="delivery-files">{grants.filter(g => !g.revoked).map(g => <li key={g.id}>{accounts.find(account => account.id === g.user_id)?.username || `#${g.user_id}`} · {t(`deliveries.roles.${g.role}`)} · {new Date(g.expires_at).toLocaleString()}<button className="action-secondary" disabled={busy} onClick={() => run(async () => { await deliveries.revoke(record.id, g.id); setGrants(await deliveries.grants(record.id)); })}>{t("deliveries.revoke")}</button></li>)}</ul></>}
    </>}
  </section>;
}

function AssessmentDetails({ result }: { result: Assessment }) {
  const messages: string[] = [];
  function collect(value: unknown) { if (Array.isArray(value)) value.forEach(collect); else if (value && typeof value === "object") { const node = value as Record<string, unknown>; if (typeof node.message === "string") messages.push(node.message); Object.values(node).filter(v => typeof v === "object").forEach(collect); } }
  collect(result.checks); collect(result.trip);
  return <ul>{[...new Set(messages)].map((message, i) => <li key={i}>{message}</li>)}</ul>;
}
