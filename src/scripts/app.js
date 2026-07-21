/**
 * Interakcje klienta. Wszystko poza modalem wpisu działa na zwykłych
 * formularzach POST — tutaj zostaje tylko to, czego nie da się zrobić samym HTML.
 */

function initYearSelects() {
  document.querySelectorAll("[data-year-select]").forEach((select) => {
    select.addEventListener("change", () => {
      const url = new URL(window.location.href);
      url.searchParams.set("year", select.value);
      window.location.assign(url.toString());
    });
  });
}

function initConfirmForms() {
  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
}

function initAutoSubmit() {
  document.querySelectorAll("[data-auto-submit]").forEach((field) => {
    field.addEventListener("change", () => field.form?.submit());
  });
}

function initPrint() {
  document.querySelectorAll("[data-print]").forEach((button) => {
    button.addEventListener("click", () => window.print());
  });
}

function initOvertimeToggle() {
  document.querySelectorAll("[data-overtime-card]").forEach((card) => {
    const wrap = card.querySelector("[data-overtime-form-wrap]");
    const typeInput = card.querySelector("[data-overtime-type]");
    card.querySelectorAll("[data-overtime-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        const selected = typeInput.value === button.dataset.overtimeMode;
        typeInput.value = selected ? "" : button.dataset.overtimeMode;
        wrap.hidden = selected;
      });
    });
  });
  document.querySelectorAll("[data-today]").forEach((input) => {
    if (!input.value) input.value = new Date().toISOString().slice(0, 10);
  });
}

const NOTES_PLACEHOLDER = {
  vacation: "np. urlop wypoczynkowy, wyjazd…",
  home_office: "np. praca zdalna, projekt X…",
  okolicznosciowy: "dodatkowe informacje…",
  bezplatny: "np. opieka nad dzieckiem, powód…",
  l4: "dodatkowe informacje…",
  za_swieto: "dodatkowe informacje…",
};

function initEntryModal() {
  const modal = document.querySelector("[data-entry-modal]");
  const form = document.querySelector("[data-entry-form]");
  if (!modal || !form) return;

  const title = modal.querySelector("[data-entry-modal-title]");
  const idInput = form.querySelector("[data-entry-id]");
  const typeInput = form.querySelector("[data-entry-type-input]");
  const dateInput = form.querySelector("[data-entry-date]");
  const notesInput = form.querySelector("[data-entry-notes]");
  const errorBox = form.querySelector("[data-entry-form-error]");
  const submit = form.querySelector("[data-entry-submit]");
  const submitLabel = form.querySelector("[data-entry-submit-label]");
  const spinner = form.querySelector("[data-entry-spinner]");

  function setType(type) {
    typeInput.value = type;
    form.querySelectorAll("[data-entry-type-button]").forEach((button) => {
      button.classList.toggle("active", button.dataset.entryType === type);
    });
    form.querySelectorAll("[data-entry-extra]").forEach((field) => {
      field.hidden = field.dataset.entryExtra !== type;
    });
    notesInput.placeholder = NOTES_PLACEHOLDER[type] || "";
  }

  function closeModal() {
    modal.hidden = true;
  }

  function openModal(entry, prefillDate = "") {
    form.reset();
    errorBox.hidden = true;
    errorBox.textContent = "";
    idInput.value = entry?.id || "";
    title.textContent = entry?.id ? "Edytuj wpis" : "Dodaj wpis";
    submitLabel.textContent = entry?.id ? "Zapisz" : "Dodaj";
    dateInput.value = entry?.date ? String(entry.date).substring(0, 10) : prefillDate;
    notesInput.value = entry?.notes || "";
    setType(entry?.type || "vacation");
    modal.hidden = false;
    dateInput.focus();
  }

  window.addEventListener("open-add", (event) => openModal(null, event.detail?.date || ""));
  window.addEventListener("open-edit", (event) => openModal(event.detail));

  form.querySelectorAll("[data-entry-type-button]").forEach((button) => {
    button.addEventListener("click", () => setType(button.dataset.entryType));
  });
  modal.querySelectorAll("[data-close-entry-modal]").forEach((button) => {
    button.addEventListener("click", closeModal);
  });
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    spinner.hidden = false;
    errorBox.hidden = true;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        credentials: "same-origin",
      });
      if (response.ok) {
        window.location.reload();
        return;
      }
      errorBox.textContent = (await response.text()) || "Wystąpił błąd. Spróbuj ponownie.";
    } catch {
      errorBox.textContent = "Brak połączenia. Spróbuj ponownie.";
    }
    errorBox.hidden = false;
    submit.disabled = false;
    spinner.hidden = true;
  });
}

function initEntryTriggers() {
  document.querySelectorAll("[data-add-entry]").forEach((day) => {
    day.addEventListener("click", () => {
      window.dispatchEvent(new CustomEvent("open-add", { detail: { date: day.dataset.date } }));
    });
  });
  document.querySelectorAll("[data-edit-entry]").forEach((button) => {
    button.addEventListener("click", () => {
      window.dispatchEvent(
        new CustomEvent("open-edit", { detail: JSON.parse(button.dataset.editEntry) }),
      );
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initEntryModal();
  initEntryTriggers();
  initYearSelects();
  initConfirmForms();
  initAutoSubmit();
  initPrint();
  initOvertimeToggle();
});
