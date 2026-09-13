/** EMCargo interface icons: one 24px grid, one stroke weight, one meaning per glyph.
 * Original interface geometry; regulatory labels remain their official artwork. */
interface IconProps { className?: string }

function glyph(path: string) {
  return function Icon({ className = "h-4 w-4" }: IconProps) {
    return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={path} /></svg>;
  };
}

export const ImportIcon = glyph("M14 2H6a2 2 0 0 0-2 2v4m10-6 6 6m-6-6v6h6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3 M2 12h10m-4-4 4 4-4 4");
export const HomeIcon = glyph("M3 3h7v7H3z M14 3h7v4h-7z M14 11h7v10h-7z M3 14h7v7H3z");
export const ShipmentsIcon = glyph("m3 7 9-5 9 5v10l-9 5-9-5z m0 0 9 5 9-5 M12 12v10 M7.5 4.5l9 5v4");
export const GroupageIcon = glyph("M3 3h6v6H3z M15 3h6v6h-6z M9 15h6v6H9z M6 9v3h12V9 M12 12v3");
export const TripsIcon = glyph("M5 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M19 21a2 2 0 1 0 0-4 2 2 0 0 0 0 4 M5 7v5a3 3 0 0 0 3 3h8a3 3 0 0 0 0-6h-5 M19 15v2");
export const LibraryIcon = glyph("M3 3h4v18H3z M10 3h4v18h-4z m7 0 4 1-1 17-4-1z");
export const SettingsIcon = glyph("M3 6h4m4 0h10 M3 18h10m4 0h4 M3 12h10m4 0h4 M7 3v6 M13 9v6 M17 15v6");
export const UserIcon = glyph("M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2");
export const LogoutIcon = glyph("M9 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4 M14 8l5 4-5 4 M8 12h11");
export const SearchIcon = glyph("M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0 m-2 5 6 6");
export const HistoryIcon = glyph("M3 11a9 9 0 1 1 2 7 M3 4v7h7 M12 7v5l3 2");
export const PasteIcon = glyph("M9 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3 M9 2h6v4H9z M8 11h8 M8 15h6");
export const PlusIcon = glyph("M12 5v14 M5 12h14");
export const ChevronDownIcon = glyph("m6 9 6 6 6-6");
export const CollapseIcon = glyph("M8 3v18 M3 3h18v18H3z m13 6-3 3 3 3");
export const MenuIcon = glyph("M4 6h16 M4 12h16 M4 18h16");
export const MoreIcon = glyph("M5 12h.01 M12 12h.01 M19 12h.01");
export const WeightIcon = glyph("M14.5 5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0 M6 8h12l3 13H3z");
export const RoadIcon = glyph("M3 5h11v12H3z M14 9h4l3 4v4h-7 M8 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0 M20 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0");
export const RailIcon = glyph("M6 3h12a2 2 0 0 1 2 2v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V5a2 2 0 0 1 2-2z M4 11h16 M12 3v8 M8 15h.01 M16 15h.01 M8 19l-3 3 M16 19l3 3");
export const SeaIcon = glyph("M5 13V7h14v6 M9 7V3h6v4 M12 10l10 4-3 6H5l-3-6z M12 10v10 M2 22c2-2 3 2 5 0s3 2 5 0 3 2 5 0 3 2 5 0");
export const InlandIcon = glyph("M2 14h20l-4 5H6z M4 14V8h4v6 M8 10h12v4 M2 22c2-2 3 2 5 0s3 2 5 0 3 2 5 0 3 2 5 0");
export const AirIcon = glyph("M10 9V4a2 2 0 0 1 4 0v5l7 5v3l-7-3v5l2 2H8l2-2v-5l-7 3v-3z");
export const MultimodalIcon = glyph("M4 7h16 M4 17h16 M4 4v6 M20 14v6 M9 4l3 3-3 3 M15 14l-3 3 3 3");
export const ArrowRightIcon = glyph("M4 12h16 m-6-6 6 6-6 6");
export const DownloadIcon = glyph("M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5");
export const RefreshIcon = glyph("M3 10a9 9 0 0 1 15-5l3 3 M21 3v5h-5 M21 14a9 9 0 0 1-15 5l-3-3 M3 21v-5h5");
export const ShieldIcon = glyph("m12 2 9 4v6c0 5-5 8-9 10-4-2-9-5-9-10V6z m-4 10 3 3 5-6");
export const DocumentIcon = glyph("M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M8 12h8 M8 16h6");
export const PaletteIcon = glyph("M21 12a9 9 0 1 0-9 9h2a2 2 0 0 0 2-2 2 2 0 0 1 2-2h1a2 2 0 0 0 2-2z M7 9h.01 M10 6h.01 M15 6h.01 M18 10h.01");
export const BuildingIcon = glyph("M4 22V3h12v19 M16 10h4v12 M8 7h4 M8 11h4 M8 15h4 M8 22v-3h4v3");
export const NetworkIcon = glyph("M9 3h6v6H9z M2 17h6v5H2z M16 17h6v5h-6z M12 9v4 M5 17v-4h14v4");
export const MailIcon = glyph("M3 4h18v16H3z m0 0 9 9 9-9");
export const CheckIcon = glyph("m5 12 4 4L19 6");
export const CloseIcon = glyph("m6 6 12 12 M6 18 18 6");
export const WarningIcon = glyph("m12 3 10 18H2z M12 9v5 M12 17h.01");
export const InfoIcon = glyph("M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 11v6 M12 7h.01");
export const LayersIcon = glyph("m12 2 10 5-10 5L2 7z M2 12l10 5 10-5 M2 17l10 5 10-5");
export const SunIcon = glyph("M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1 1 M18 18l1 1 M5 19l1-1 M18 6l1-1");
export const MoonIcon = glyph("M21 13A9 9 0 0 1 11 3 9 9 0 1 0 21 13");
export const MonitorIcon = glyph("M3 3h18v14H3z M12 17v4 M8 21h8");

export const ErrorIcon = glyph("M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 m-13-3 6 6 M9 15l6-6");
export const PenIcon = glyph("m4 16 12-12 4 4-12 12-5 1z M14 6l4 4 M3 21h8");
export const UploadIcon = glyph("M12 16V3 m-5 5 5-5 5 5 M3 16v5h18v-5");
export const CopyIcon = glyph("M9 9h12v12H9z M15 9V3H3v12h6");
export const CodeIcon = glyph("m8 6-6 6 6 6 M16 6l6 6-6 6 m-3-15-2 18");
export const TrashIcon = glyph("M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7");
