// ── Year selector ────────────────────────────────────────────
function changeYear(year) {
  const url = new URL(window.location);
  url.searchParams.set('year', year);
  window.location = url.toString();
}

// ── Confirm delete (calendar + history) ─────────────────────
function confirmDelete(id, label) {
  if (!confirm('Usunąć wpis z dnia ' + label + '?')) return;
  htmx.ajax('POST', '/entries/' + id + '/delete', { target: 'body', swap: 'none' });
}

// ── Alpine.js shell component ────────────────────────────────
function shell() {
  return {
    modalOpen: false,
    editId: null,
    entryType: 'vacation',
    entryDate: '',
    entryNotes: '',
    okolReason: '',
    l4Number: '',
    zaSwietoDay: '',
    formLoading: false,
    formError: '',

    init() {
      window.addEventListener('open-add', (e) => this.openModal(null, e.detail?.date));
      window.addEventListener('open-edit', (e) => this.openModal(e.detail));
    },

    openModal(entry = null, prefillDate = '') {
      this.formError = '';
      this.formLoading = false;
      this.okolReason = '';
      this.l4Number = '';
      this.zaSwietoDay = '';
      if (entry && entry.id) {
        this.editId     = entry.id;
        this.entryType  = entry.type || 'vacation';
        this.entryDate  = entry.date ? String(entry.date).substring(0, 10) : '';
        this.entryNotes = entry.notes || '';
      } else {
        this.editId     = null;
        this.entryType  = 'vacation';
        this.entryDate  = prefillDate || '';
        this.entryNotes = '';
      }
      this.modalOpen = true;
    },

    notesPlaceholder() {
      const map = {
        vacation:        'np. urlop wypoczynkowy, wyjazd…',
        home_office:     'np. praca zdalna, projekt X…',
        okolicznościowy: 'dodatkowe informacje…',
        bezplatny:       'np. opieka nad dzieckiem, powód…',
        l4:              'dodatkowe informacje…',
        za_swieto:       'dodatkowe informacje…',
      };
      return map[this.entryType] || '';
    },

    onFormResponse(event) {
      this.formLoading = false;
      if (event.detail.successful) {
        this.modalOpen = false;
        window.location.reload();
      } else {
        this.formError = event.detail.xhr?.responseText || 'Wystąpił błąd. Spróbuj ponownie.';
      }
    },
  };
}

// ── Alpine.js calendar component ─────────────────────────────
function calendarPage() {
  return {
    handleDayClick(el) {
      if (el.dataset.inMonth !== 'true') return;
      if (el.classList.contains('cal-day--weekend')) return;
      if (el.dataset.hasEntries === 'true') return;
      window.dispatchEvent(new CustomEvent('open-add', { detail: { date: el.dataset.date } }));
    },
  };
}

// ── Chart.js monthly chart ───────────────────────────────────
function initChart(canvasId, stats) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: stats.map(m => m.label),
      datasets: [
        {
          label: 'Urlop',
          data: stats.map(m => m.vacation),
          backgroundColor: 'rgba(179,157,219,0.75)',
          borderRadius: 4,
          borderSkipped: false,
        },
        {
          label: 'Home Office',
          data: stats.map(m => m.home_office),
          backgroundColor: 'rgba(128,203,196,0.75)',
          borderRadius: 4,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#CAC4D0', font: { size: 12 }, boxWidth: 12, boxHeight: 12 },
        },
        tooltip: {
          backgroundColor: '#2D2B32',
          titleColor: '#E6E1E5',
          bodyColor: '#CAC4D0',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          cornerRadius: 8,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.raw} dni`,
          },
        },
      },
      scales: {
        x: {
          ticks: { color: '#938F99', font: { size: 11 } },
          grid:  { color: 'rgba(255,255,255,0.05)', drawBorder: false },
        },
        y: {
          ticks: { color: '#938F99', font: { size: 11 }, stepSize: 1 },
          grid:  { color: 'rgba(255,255,255,0.05)', drawBorder: false },
          beginAtZero: true,
        },
      },
    },
  });
}
