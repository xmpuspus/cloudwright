import React from "react";

/** Stroke icons on a 24x24 grid. One component so weight and joins stay consistent. */
const PATHS: Record<string, string> = {
  cloud: "M17.5 19a4.5 4.5 0 00.5-8.97A6 6 0 006.08 11.5 3.5 3.5 0 006.5 19h11z",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z",
  stop: "M7 7h10v10H7z",
  plus: "M12 5v14M5 12h14",
  close: "M6 6l12 12M18 6L6 18",
  chevron: "M6 9l6 6 6-6",
  check: "M4 12.5l5 5 11-11",
  cross: "M6 6l12 12M18 6L6 18",
  sun: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6L4.2 4.2M19.8 19.8l-1.4-1.4M18.4 5.6l1.4-1.4M4.2 19.8l1.4-1.4M16 12a4 4 0 11-8 0 4 4 0 018 0z",
  moon: "M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z",
  download: "M12 3v12M7 11l5 5 5-5M4 20h16",
  copy: "M9 9h10v10H9zM5 15V5h10",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.5-4.5",
  layers: "M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 17l9 5 9-5",
  alert: "M12 8v5M12 17h.01M10.3 3.9L2.4 17.5A2 2 0 004.1 20.5h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z",
  panel: "M4 4h16v16H4zM10 4v16",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  chat: "M21 12a8 8 0 01-11.6 7.1L4 20l1-4.5A8 8 0 1121 12z",
  refresh: "M20 12a8 8 0 10-2.3 5.6M20 6v6h-6",
};

export type IconName = keyof typeof PATHS | string;

export function Icon({
  name,
  size = 16,
  strokeWidth = 1.8,
  className,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  const d = PATHS[name] ?? PATHS.cloud;
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={{ display: "block", flexShrink: 0 }}
    >
      <path d={d} />
    </svg>
  );
}

export default Icon;
