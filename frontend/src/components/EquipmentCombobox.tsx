import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { api, CatalogSearchHit, EquipmentItem, EquipmentSnapshot } from "../api/client";
import { equipmentSnapshot } from "../utils/equipment";
import { documentLanguage } from "../i18n/language";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2.5 text-sm min-h-[44px]";

const MIN_SEARCH_LEN = 2;
const DEBOUNCE_MS = 280;

interface Props {
  id?: string;
  value: string;
  onChange: (value: string, equipment?: EquipmentSnapshot | null) => void;
  placeholder?: string;
  /** The input itself, so a caller can put the cursor in it — the goods step
   *  focuses the description of a line it has just added. */
  inputRef?: (element: HTMLInputElement | null) => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLInputElement>) => void;
  "aria-label"?: string;
}

/** The library, fetched once for every box on the screen.
 *
 *  One box per line means fifty identical requests on a fifty-line import,
 *  which is fifty times the same answer and a visible stall. The promise is
 *  shared; a failure is not cached, so a box mounted after the network came
 *  back asks again. */
let libraryPromise: Promise<EquipmentItem[]> | null = null;
export function invalidateEquipmentLibrary() { libraryPromise = null; }

function library(): Promise<EquipmentItem[]> {
  if (!libraryPromise) {
    libraryPromise = api.listEquipment().catch((error) => {
      libraryPromise = null;
      throw error;
    });
  }
  return libraryPromise;
}

export default function EquipmentCombobox({
  id,
  value,
  onChange,
  placeholder,
  inputRef: exposeInput,
  onKeyDown,
  ...rest
}: Props) {
  const { t, i18n } = useTranslation();
  const [equipment, setEquipment] = useState<EquipmentItem[]>([]);
  const [results, setResults] = useState<CatalogSearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const [menuPos, setMenuPos] = useState<{ left: number; top: number; width: number; maxHeight: number } | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLUListElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    library().then(setEquipment).catch(() => setEquipment([]));
  }, []);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node;
      if (wrapRef.current?.contains(target)) return;
      if (menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const updatePosition = useCallback(() => {
    const el = inputRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const gap = 4;
    const menuMax = 224;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    let top: number;
    let maxHeight: number;
    if (spaceBelow >= 160 || spaceBelow >= spaceAbove) {
      top = rect.bottom + gap;
      maxHeight = Math.max(120, Math.min(menuMax, spaceBelow));
    } else {
      maxHeight = Math.max(120, Math.min(menuMax, spaceAbove));
      top = rect.top - gap - maxHeight;
    }
    setMenuPos({ left: rect.left, top, width: rect.width, maxHeight });
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const handler = () => updatePosition();
    window.addEventListener("resize", handler);
    window.addEventListener("scroll", handler, true);
    return () => {
      window.removeEventListener("resize", handler);
      window.removeEventListener("scroll", handler, true);
    };
  }, [open, updatePosition]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    // Only while the list is open, which means only while somebody is actually
    // looking at it. A box that searched for whatever it was mounted with sent
    // one request per line: a fifty-line import fired fifty catalogue searches
    // at once and made the weights take seconds longer to appear.
    const q = open ? query.trim() : "";
    if (q.length < MIN_SEARCH_LEN) {
      setResults([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(() => {
      api
        .catalogSearch(q, 25, documentLanguage(i18n.language))
        .then((res) => setResults(res.results))
        .catch(() => setResults([]))
        .finally(() => setLoading(false));
    }, DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // On the language too: whoever switches language while typing should get
    // the suggestions back in the new language.
  }, [query, open, i18n.language]);

  const browseEquipment = useMemo(() => {
    if (query.trim().length >= MIN_SEARCH_LEN) return [];
    return equipment.filter((e) => e.active !== false).slice(0, 40);
  }, [equipment, query]);

  // The typed text lives here as well as in the parent, and until v1.54.0 it
  // never came back from the parent. With one box on screen that is invisible;
  // with two — the table row and the same row in the detail panel — they drift
  // apart the moment you type in one of them, and the stale one overwrites the
  // other as soon as you touch it. The parent updates on every keystroke, so
  // this is a no-op while typing and a correction the rest of the time.
  useEffect(() => {
    setQuery(value);
  }, [value]);

  const sourceLabel = (source: CatalogSearchHit["source"]) => t(`review.catalogSource.${source}` as "review.catalogSource.equipment");

  const pickValue = (label: string, item?: EquipmentSnapshot | null) => {
    setQuery(label);
    onChange(label, item ?? null);
    setOpen(false);
  };

  const showCatalog = query.trim().length >= MIN_SEARCH_LEN;

  return (
    <div ref={wrapRef} className="relative">
      <input
        id={id}
        ref={(element) => {
          inputRef.current = element;
          exposeInput?.(element);
        }}
        className={inputClass}
        value={query}
        aria-label={rest["aria-label"]}
        onKeyDown={(event) => {
          // Escape closes the list rather than the dialog or the page behind
          // it, and Tab leaves the field with the list closed. Without this the
          // suggestions stayed open over whatever came next, taking the clicks
          // meant for it — which is what the goods step's own Add line button
          // ran into.
          if (event.key === "Escape" && open) {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
            return;
          }
          if (event.key === "Tab") setOpen(false);
          if (event.key === "Enter") setOpen(false);
          onKeyDown?.(event);
        }}
        placeholder={placeholder || t("review.descriptionPlaceholder")}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(e.target.value, null);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        autoComplete="off"
      />
      {open && menuPos && createPortal(
        <ul
          ref={menuRef}
          className="fixed z-50 overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
          style={{ left: menuPos.left, top: menuPos.top, width: menuPos.width, maxHeight: menuPos.maxHeight }}
        >
          <li>
            <button
              type="button"
              className="w-full px-3 py-2.5 text-left text-sm text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"
              onClick={() => pickValue(query)}
            >
              {t("review.customDescription")}
            </button>
          </li>

          {showCatalog && loading && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">{t("review.catalogSearching")}</li>
          )}

          {showCatalog &&
            !loading &&
            results.map((hit) => (
              <li key={hit.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2.5 text-left hover:bg-brand-50 dark:hover:bg-brand-950/40 border-t border-slate-100 dark:border-slate-800"
                  onClick={() => pickValue(hit.value, hit.equipment)}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{hit.label}</span>
                    <span className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">{sourceLabel(hit.source)}</span>
                  </span>
                  {hit.sublabel && (
                    <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{hit.sublabel}</span>
                  )}
                </button>
              </li>
            ))}

          {showCatalog && !loading && results.length === 0 && (
            <li className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">{t("review.noCatalogMatch")}</li>
          )}

          {!showCatalog &&
            browseEquipment.map((item) => {
              const label = item.specifications;
              const sub = item.asset_code || item.container_number || item.registration || null;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className="w-full px-3 py-2.5 text-left hover:bg-brand-50 dark:hover:bg-brand-950/40 border-t border-slate-100 dark:border-slate-800"
                    onClick={() => pickValue(label, equipmentSnapshot(item))}
                  >
                    <span className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{label}</span>
                      <span className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">
                        {sourceLabel("equipment")}
                      </span>
                    </span>
                    {sub && <span className="block text-xs text-slate-500 dark:text-slate-400 truncate">{sub}</span>}
                    <span className="block text-xs text-slate-400 dark:text-slate-500">{item.weight_kg} kg</span>
                  </button>
                </li>
              );
            })}
        </ul>,
        document.body,
      )}
    </div>
  );
}
