import type { APIRoute } from "astro";
import { env } from "cloudflare:workers";
import { getHistoryEntries } from "@/lib/db";
import { parseOptionalMonth, parseYear } from "@/lib/dates";
import { getLeaveTypeMeta } from "@/lib/leaveTypes";

function csvCell(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}

export const GET: APIRoute = async ({ url }) => {
  const year = parseYear(url.searchParams.get("year"));
  const typeFilter = url.searchParams.get("type") || "";
  const month = parseOptionalMonth(url.searchParams.get("month"));
  const entries = (await getHistoryEntries(env.DB, year, typeFilter, month)).sort((a, b) =>
    a.date.localeCompare(b.date),
  );

  const lines = [["Data", "Typ", "Notatka"].map(csvCell).join(",")];
  for (const entry of entries) {
    lines.push(
      [entry.date.substring(0, 10), getLeaveTypeMeta(entry.type).fullLabel, entry.notes || ""]
        .map(csvCell)
        .join(","),
    );
  }

  return new Response(lines.join("\r\n") + "\r\n", {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename=urlopy_${year}${month ? `_${String(month).padStart(2, "0")}` : ""}.csv`,
    },
  });
};
