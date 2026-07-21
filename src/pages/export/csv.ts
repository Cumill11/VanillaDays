import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { getHistoryEntries } from "@/lib/db";
import { parseYear } from "@/lib/dates";

const TYPE_LABELS: Record<string, string> = {
  vacation: "Urlop",
  home_office: "Home Office",
  okolicznosciowy: "Urlop okolicznościowy",
  bezplatny: "Urlop bezpłatny",
  l4: "L4",
  za_swieto: "Urlop za święto",
};

/** Zabezpieczenie przed wykonaniem formuły po otwarciu pliku w arkuszu. */
function csvSafe(value: unknown): string {
  const text = value == null ? "" : String(value);
  return ["=", "+", "-", "@", "\t", "\r"].includes(text[0] || "") ? `'${text}` : text;
}

function csvCell(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}

export const GET: APIRoute = async ({ url }) => {
  const year = parseYear(url.searchParams.get("year"));
  const typeFilter = url.searchParams.get("type") || "";
  const entries = (await getHistoryEntries(env.DB, year, typeFilter, null)).sort((a, b) =>
    a.date.localeCompare(b.date),
  );

  const lines = [["Data", "Typ", "Notatka"].map(csvCell).join(",")];
  for (const entry of entries) {
    lines.push(
      [
        csvSafe(entry.date.substring(0, 10)),
        csvSafe(TYPE_LABELS[entry.type] || entry.type),
        csvSafe(entry.notes || ""),
      ]
        .map(csvCell)
        .join(","),
    );
  }

  return new Response(`﻿${lines.join("\r\n")}\r\n`, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename=urlopy_${year}.csv`,
    },
  });
};
