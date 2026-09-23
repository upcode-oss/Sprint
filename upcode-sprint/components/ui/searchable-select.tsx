"use client";

import { Check, ChevronDown, Search, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";

export interface SearchableSelectOption {
  value: string;
  label: string;
  description?: string;
}

interface BaseProps {
  options: SearchableSelectOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  emptyLabel?: string;
}

function useSearchableOptions(options: SearchableSelectOption[], open: boolean) {
  const root = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const filtered = useMemo(() => {
    const search = query.trim().toLocaleLowerCase();
    if (!search) return options;
    return options.filter((option) => `${option.label} ${option.description ?? ""}`.toLocaleLowerCase().includes(search));
  }, [options, query]);

  return { filtered, query, root, setQuery };
}

function OptionList({
  options,
  selected,
  onSelect,
  emptyLabel,
}: {
  options: SearchableSelectOption[];
  selected: Set<string>;
  onSelect: (value: string) => void;
  emptyLabel: string;
}) {
  if (!options.length) return <div className="searchable-select-empty">{emptyLabel}</div>;
  return <div className="searchable-select-options" role="listbox">{options.map((option) => {
    const active = selected.has(option.value);
    return <button type="button" className={`searchable-select-option ${active ? "active" : ""}`} key={option.value} onClick={() => onSelect(option.value)} role="option" aria-selected={active}><span><strong>{option.label}</strong>{option.description ? <small>{option.description}</small> : null}</span>{active ? <Check /> : null}</button>;
  })}</div>;
}

function Menu({
  query,
  setQuery,
  searchPlaceholder,
  children,
}: {
  query: string;
  setQuery: (value: string) => void;
  searchPlaceholder: string;
  children: ReactNode;
}) {
  return <div className="searchable-select-menu"><div className="searchable-select-search"><Search /><input autoFocus className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={searchPlaceholder} aria-label={searchPlaceholder} /></div>{children}</div>;
}

export function SearchableSelect({
  options,
  value,
  onValueChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyLabel = "No matches found.",
  disabled = false,
}: BaseProps & { value: string; onValueChange: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const { filtered, query, root, setQuery } = useSearchableOptions(options, open);
  const current = options.find((option) => option.value === value);

  useEffect(() => {
    function close(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [root]);

  return <div className="searchable-select" ref={root} onKeyDown={(event) => event.key === "Escape" && setOpen(false)}><button type="button" className="input searchable-select-trigger" onClick={() => setOpen((currentOpen) => !currentOpen)} disabled={disabled} aria-expanded={open} aria-haspopup="listbox"><span className={current ? "" : "muted"}>{current?.label ?? placeholder}</span><ChevronDown /></button>{open ? <Menu query={query} setQuery={setQuery} searchPlaceholder={searchPlaceholder}><OptionList options={filtered} selected={new Set(current ? [value] : [])} emptyLabel={emptyLabel} onSelect={(next) => { onValueChange(next); setOpen(false); }} /></Menu> : null}</div>;
}

export function SearchableMultiSelect({
  options,
  values,
  onValuesChange,
  placeholder = "Select…",
  searchPlaceholder = "Search…",
  emptyLabel = "No matches found.",
  disabled = false,
}: BaseProps & { values: string[]; onValuesChange: (values: string[]) => void }) {
  const [open, setOpen] = useState(false);
  const { filtered, query, root, setQuery } = useSearchableOptions(options, open);
  const selected = new Set(values);

  useEffect(() => {
    function close(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [root]);

  function toggle(next: string) {
    onValuesChange(selected.has(next) ? values.filter((value) => value !== next) : [...values, next]);
  }

  return <div className="searchable-select" ref={root} onKeyDown={(event) => event.key === "Escape" && setOpen(false)}><button type="button" className="input searchable-select-trigger" onClick={() => setOpen((currentOpen) => !currentOpen)} disabled={disabled} aria-expanded={open} aria-haspopup="listbox"><span className={values.length ? "" : "muted"}>{values.length ? `${values.length} selected` : placeholder}</span><ChevronDown /></button>{values.length ? <div className="searchable-select-tags">{values.map((value) => { const option = options.find((item) => item.value === value); return option ? <span className="searchable-select-tag" key={value}>{option.label}<button type="button" onClick={() => toggle(value)} disabled={disabled} aria-label={`Remove ${option.label}`}><X /></button></span> : null; })}</div> : null}{open ? <Menu query={query} setQuery={setQuery} searchPlaceholder={searchPlaceholder}><OptionList options={filtered} selected={selected} onSelect={toggle} emptyLabel={emptyLabel} /></Menu> : null}</div>;
}
