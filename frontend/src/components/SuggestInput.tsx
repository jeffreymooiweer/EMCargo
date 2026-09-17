import { ReactNode, useEffect, useId, useRef, useState } from "react";

const inputClass =
  "w-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-sm";

export interface SuggestItem<T> {
  key: string;
  data: T;
  render: ReactNode;
}

interface Props<T> {
  id?: string;
  ariaLabel?: string;
  value: string;
  onChange: (value: string) => void;
  onPick: (item: T) => void;
  fetcher: (q: string) => Promise<SuggestItem<T>[]>;
  placeholder?: string;
  minLength?: number;
  onBlur?: () => void;
  className?: string;
}

/** A free-text combobox; selecting a suggestion works with keys, touch or mouse. */
export default function SuggestInput<T>({
  id, ariaLabel, value, onChange, onPick, fetcher, placeholder,
  minLength = 2, onBlur, className,
}: Props<T>) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const listId = `${inputId}-options`;
  const [items, setItems] = useState<SuggestItem<T>[]>([]);
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(false);
  const [active, setActive] = useState(-1);
  const timer = useRef<number | undefined>(undefined);
  const latest = useRef(0);
  const fetchRef = useRef(fetcher);
  fetchRef.current = fetcher;
  const expanded = open && !picked && items.length > 0;

  useEffect(() => {
    const request = ++latest.current;
    window.clearTimeout(timer.current);
    setItems([]);
    setActive(-1);
    if (open && !picked && value.trim().length >= minLength) {
      timer.current = window.setTimeout(() => {
        void fetchRef.current(value).then(results => {
          if (latest.current === request) setItems(results);
        }).catch(() => {
          if (latest.current === request) setItems([]);
        });
      }, 250);
    }
    return () => {
      ++latest.current;
      window.clearTimeout(timer.current);
    };
  }, [value, open, picked, minLength]);

  useEffect(() => {
    if (expanded && active >= 0) document.getElementById(`${listId}-${active}`)?.scrollIntoView?.({ block: "nearest" });
  }, [active, expanded, listId]);

  function close() {
    ++latest.current;
    window.clearTimeout(timer.current);
    setOpen(false);
    setItems([]);
    setActive(-1);
  }

  function choose(item: SuggestItem<T>) {
    close();
    setPicked(true);
    onPick(item.data);
  }

  return (
    <div className="relative min-w-0">
      <input
        id={inputId}
        aria-label={ariaLabel}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={expanded ? listId : undefined}
        aria-activedescendant={expanded && active >= 0 ? `${listId}-${active}` : undefined}
        className={className ?? inputClass}
        value={value}
        placeholder={placeholder}
        onChange={event => {
          ++latest.current;
          setItems([]);
          setActive(-1);
          setPicked(false);
          setOpen(true);
          onChange(event.target.value);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => { close(); onBlur?.(); }}
        onKeyDown={event => {
          if (event.isDefaultPrevented() || event.nativeEvent.isComposing) return;
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setPicked(false);
            setOpen(true);
            if (items.length) {
              setActive(index => event.key === "ArrowDown"
                ? (index + 1) % items.length
                : index <= 0 ? items.length - 1 : index - 1);
            }
          } else if (event.key === "Enter" && expanded && active >= 0) {
            event.preventDefault();
            event.stopPropagation();
            choose(items[active]);
          } else if (event.key === "Escape" && open) {
            event.preventDefault();
            event.stopPropagation();
            close();
          }
        }}
        autoComplete="off"
      />
      {expanded && (
        <ul id={listId} role="listbox" aria-label={ariaLabel ?? placeholder}
          className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
          {items.map((item, index) => (
            <li key={item.key} id={`${listId}-${index}`} role="option" aria-selected={active === index}
              onMouseDown={event => event.preventDefault()}
              onClick={() => choose(item)}
              className={`min-h-[44px] cursor-pointer px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800 ${active === index ? "bg-brand-50 dark:bg-slate-800" : ""}`}>
              {item.render}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
