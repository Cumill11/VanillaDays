import { ActionError, defineAction } from "astro:actions";
import { z } from "astro:schema";
import { env } from "cloudflare:workers";

const dateField = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Nieprawidłowa data");

export const server = {
  saveEntry: defineAction({
    accept: "form",
    input: z.object({
      id: z.string().optional(),
      date: dateField,
      type: z.enum(["vacation", "home_office", "okolicznosciowy", "bezplatny", "l4", "za_swieto"]),
      okol_reason: z.string().optional(),
      l4_number: z.string().optional(),
      za_swieto_day: z.string().optional(),
      notes: z.string().optional(),
    }),
    handler: async (input) => {
      let notes = (input.notes || "").trim();
      if (input.type === "okolicznosciowy" && input.okol_reason) {
        notes = input.okol_reason + (notes ? ` | ${notes}` : "");
      }
      if (input.type === "l4" && input.l4_number) {
        notes = `ZUS: ${input.l4_number}` + (notes ? ` | ${notes}` : "");
      }
      if (input.type === "za_swieto" && input.za_swieto_day) {
        notes = `Za: ${input.za_swieto_day}` + (notes ? ` | ${notes}` : "");
      }
      if (notes.length > 500) {
        throw new ActionError({ code: "BAD_REQUEST", message: "Notatka jest za długa" });
      }
      const noteValue = notes || null;
      const id = Number.parseInt(input.id || "", 10);

      try {
        if (Number.isFinite(id)) {
          await env.DB.prepare(
            "UPDATE leave_entries SET date = ?, type = ?, notes = ? WHERE id = ?",
          )
            .bind(input.date, input.type, noteValue, id)
            .run();
        } else {
          await env.DB.prepare("INSERT INTO leave_entries (date, type, notes) VALUES (?, ?, ?)")
            .bind(input.date, input.type, noteValue)
            .run();
        }
      } catch {
        throw new ActionError({ code: "CONFLICT", message: "Wpis dla tej daty już istnieje" });
      }
    },
  }),

  deleteEntry: defineAction({
    accept: "form",
    input: z.object({ id: z.number() }),
    handler: async ({ id }) => {
      await env.DB.prepare("DELETE FROM leave_entries WHERE id = ?").bind(id).run();
    },
  }),

  saveOvertime: defineAction({
    accept: "form",
    input: z.object({
      date: dateField,
      type: z.enum(["earned", "taken"]),
      hours: z.number().positive("Liczba godzin musi być większa od 0"),
      notes: z.string().optional(),
    }),
    handler: async (input) => {
      await env.DB.prepare(
        "INSERT INTO overtime_log (date, hours, type, notes) VALUES (?, ?, ?, ?)",
      )
        .bind(input.date, input.hours, input.type, input.notes?.trim() || null)
        .run();
    },
  }),

  deleteOvertime: defineAction({
    accept: "form",
    input: z.object({ id: z.number() }),
    handler: async ({ id }) => {
      await env.DB.prepare("DELETE FROM overtime_log WHERE id = ?").bind(id).run();
    },
  }),

  saveSettings: defineAction({
    accept: "form",
    input: z.object({
      year: z.number(),
      vacation_limit: z.number().min(0).max(100),
      ho_limit: z.number().min(0).max(260),
      vacation_carried_over: z.number().min(0).max(50),
    }),
    handler: async (input) => {
      await env.DB.prepare(
        "UPDATE year_config SET vacation_limit = ?, ho_limit = ?, vacation_carried_over = ? WHERE year = ?",
      )
        .bind(
          Math.round(input.vacation_limit),
          Math.round(input.ho_limit),
          Math.round(input.vacation_carried_over),
          input.year,
        )
        .run();
      return { year: input.year };
    },
  }),
};
