/* Personal Finance Bot — Telegram Mini App Frontend (RU / EN / DE) */

const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) {
  tg.ready();
  tg.expand();
}

const I18N = {
  ru: {
    current_balance: "Текущий баланс",
    monthly_income: "Доходы за месяц",
    monthly_expense: "Расходы за месяц",
    main_menu: "Основное меню",
    btn_add_expense: "Добавить расход",
    btn_add_income: "Добавить доход",
    btn_stats: "Статистика",
    btn_history: "История",
    btn_recurring: "Регулярные",
    btn_partner: "Партнёр",
    btn_profile: "Мой профиль и настройки",
    btn_add_rec: "+ Добавить",
    stats_title: "📊 Финансовая статистика",
    stat_today_exp: "Расходы за день",
    stat_week_exp: "Расходы за неделю",
    stat_month_exp: "Расходы за месяц",
    stat_total_inc: "Общие доходы",
    stat_month_card: "💳 Оплата картой (месяц)",
    stat_month_cash: "💵 Наличными (месяц)",
    stat_net_diff: "Разница (доходы − расходы)",
    history_title: "🕒 История операций",
    partner_title: "🤝 Партнёрский режим",
    your_partner_code: "Ваш личный партнёрский код:",
    partner_name_lbl: "Партнёр",
    partner_balance_lbl: "Баланс партнёра",
    partner_inc_lbl: "Доходы за месяц",
    partner_exp_lbl: "Расходы за месяц",
    partner_history_lbl: "🕒 История партнёра",
    lbl_name: "Имя пользователя",
    lbl_phone: "Номер телефона",
    lbl_country: "Страна",
    lbl_currency: "Основная валюта (ISO 4217)",
    lbl_timezone: "Часовой пояс",
    lbl_language: "Язык интерфейса",
    lbl_notify_rec: "Уведомления о регулярных платежах",
    lbl_daily_rem: "Напоминания о записи расходов",
    lbl_reg_date: "Дата регистрации:",
    btn_save_profile: "Сохранить настройки",
    lbl_amount: "Сумма",
    lbl_desc: "Магазин или описание (необязательно)",
    lbl_payment_method: "Способ оплаты",
    opt_pay_card: "💳 Карта",
    opt_pay_cash: "💵 Наличные",
    btn_save: "Сохранить",
    add_rec_title: "Новая регулярная операция",
    lbl_type: "Тип операции",
    lbl_title: "Название",
    lbl_period: "Периодичность",
    lbl_next_date: "Дата следующего списания/начисления",
    quick_placeholder: "Быстрый ввод: 6.1 lidl, 12.50, +1500 Зарплата...",
    empty_history: "Операций пока нет. Введите сумму выше!",
    empty_recurring: "Регулярных операций пока нет.",
    saved_expense: "Расход сохранён • Успешно",
    saved_income: "Доход сохранён • Успешно",
  },
  en: {
    current_balance: "Current Balance",
    monthly_income: "Monthly Income",
    monthly_expense: "Monthly Expenses",
    main_menu: "Main Menu",
    btn_add_expense: "Add Expense",
    btn_add_income: "Add Income",
    btn_stats: "Statistics",
    btn_history: "History",
    btn_recurring: "Recurring",
    btn_partner: "Partner",
    btn_profile: "My Profile & Settings",
    btn_add_rec: "+ Add",
    stats_title: "📊 Financial Statistics",
    stat_today_exp: "Today's Expenses",
    stat_week_exp: "Weekly Expenses",
    stat_month_exp: "Monthly Expenses",
    stat_total_inc: "Total Income",
    stat_month_card: "💳 Paid by Card (Month)",
    stat_month_cash: "💵 Paid in Cash (Month)",
    stat_net_diff: "Net Difference (income − expenses)",
    history_title: "🕒 Transaction History",
    partner_title: "🤝 Partner Mode",
    your_partner_code: "Your Personal Partner Code:",
    partner_name_lbl: "Partner",
    partner_balance_lbl: "Partner's Balance",
    partner_inc_lbl: "Monthly Income",
    partner_exp_lbl: "Monthly Expenses",
    partner_history_lbl: "🕒 Partner History",
    lbl_name: "Name",
    lbl_phone: "Phone Number",
    lbl_country: "Country",
    lbl_currency: "Primary Currency (ISO 4217)",
    lbl_timezone: "Timezone",
    lbl_language: "Interface Language",
    lbl_notify_rec: "Recurring Payment Notifications",
    lbl_daily_rem: "Daily Expense Reminders",
    lbl_reg_date: "Registered:",
    btn_save_profile: "Save Settings",
    lbl_amount: "Amount",
    lbl_desc: "Store or Description (optional)",
    lbl_payment_method: "Payment Method",
    opt_pay_card: "💳 Card",
    opt_pay_cash: "💵 Cash",
    btn_save: "Save",
    add_rec_title: "New Recurring Operation",
    lbl_type: "Operation Type",
    lbl_title: "Title",
    lbl_period: "Frequency",
    lbl_next_date: "Next Execution Date",
    quick_placeholder: "Quick entry: 6.1 lidl, 12.50, +1500 Salary...",
    empty_history: "No transactions yet. Enter an amount above!",
    empty_recurring: "No recurring operations yet.",
    saved_expense: "Expense Saved • Success",
    saved_income: "Income Saved • Success",
  },
  de: {
    current_balance: "Aktueller Kontostand",
    monthly_income: "Einnahmen (Monat)",
    monthly_expense: "Ausgaben (Monat)",
    main_menu: "Hauptmenü",
    btn_add_expense: "Ausgabe +",
    btn_add_income: "Einnahme +",
    btn_stats: "Statistik",
    btn_history: "Verlauf",
    btn_recurring: "Regelmäßig",
    btn_partner: "Partner",
    btn_profile: "Mein Profil & Einstellungen",
    btn_add_rec: "+ Neu",
    stats_title: "📊 Finanzstatistik",
    stat_today_exp: "Ausgaben heute",
    stat_week_exp: "Ausgaben (Woche)",
    stat_month_exp: "Ausgaben (Monat)",
    stat_total_inc: "Gesamteinnahmen",
    stat_month_card: "💳 Kartenzahlung (Monat)",
    stat_month_cash: "💵 Bargeld (Monat)",
    stat_net_diff: "Differenz (Einnahmen − Ausgaben)",
    history_title: "🕒 Transaktionsverlauf",
    partner_title: "🤝 Partner-Modus",
    your_partner_code: "Ihr persönlicher Partner-Code:",
    partner_name_lbl: "Partner",
    partner_balance_lbl: "Kontostand (Partner)",
    partner_inc_lbl: "Einnahmen (Monat)",
    partner_exp_lbl: "Ausgaben (Monat)",
    partner_history_lbl: "🕒 Partner-Verlauf",
    lbl_name: "Name",
    lbl_phone: "Telefonnummer",
    lbl_country: "Land",
    lbl_currency: "Hauptwährung (ISO 4217)",
    lbl_timezone: "Zeitzone",
    lbl_language: "Sprache",
    lbl_notify_rec: "Benachrichtigungen für regelm. Zahlungen",
    lbl_daily_rem: "Tägliche Ausgaben-Erinnerung",
    lbl_reg_date: "Registriert am:",
    btn_save_profile: "Einstellungen speichern",
    lbl_amount: "Betrag",
    lbl_desc: "Geschäft oder Beschreibung (optional)",
    lbl_payment_method: "Zahlungsmethode",
    opt_pay_card: "💳 Karte",
    opt_pay_cash: "💵 Bargeld",
    btn_save: "Speichern",
    add_rec_title: "Neue regelmäßige Buchung",
    lbl_type: "Buchungstyp",
    lbl_title: "Name",
    lbl_period: "Intervall",
    lbl_next_date: "Nächstes Ausführungsdatum",
    quick_placeholder: "Schnelleingabe: 6.1 lidl, 12.50, +1500 Gehalt...",
    empty_history: "Noch keine Buchungen vorhanden.",
    empty_recurring: "Noch keine regelmäßigen Buchungen.",
    saved_expense: "Ausgabe gespeichert • Erfolgreich",
    saved_income: "Einnahme gespeichert • Erfolgreich",
  },
};

let appState = {
  lang: "ru",
  user: null,
  stats: null,
  transactions: [],
  recurring: [],
  partner_info: null,
  catalog: null,
};

function getAuthHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (tg && tg.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  }
  const params = new URLSearchParams(window.location.search);
  const uid = params.get("uid");
  if (uid) {
    headers["X-Telegram-User-Id"] = uid;
  }
  return headers;
}

function showToast(htmlText) {
  const el = document.getElementById("toast-banner");
  el.innerHTML = htmlText;
  el.classList.remove("hidden");
  setTimeout(() => {
    el.classList.add("hidden");
  }, 3500);
}

function normalizeLang(lang) {
  const l = String(lang || "ru").toLowerCase();
  if (l.startsWith("de")) return "de";
  if (l.startsWith("en")) return "en";
  return "ru";
}

function applyLanguage(lang) {
  appState.lang = normalizeLang(lang);
  const dict = I18N[appState.lang];
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (dict[key]) {
      el.textContent = dict[key];
    }
  });
  const qInput = document.getElementById("quick-input");
  if (qInput) {
    qInput.placeholder = dict.quick_placeholder;
  }
}

async function fetchDashboard() {
  const res = await fetch(`/api/dashboard${window.location.search}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return;
  const data = await res.json();
  appState.user = data.user;
  appState.stats = data.stats;
  appState.transactions = data.transactions;
  appState.recurring = data.recurring;
  appState.partner_info = data.partner_info;
  appState.catalog = data.catalog;

  applyLanguage(data.user.language);
  renderDashboard();
}

function renderDashboard() {
  const { user, stats, transactions, recurring, partner_info, catalog } = appState;
  const dict = I18N[appState.lang];

  document.getElementById("currency-badge").textContent = `${user.currency} • ${user.timezone}`;
  document.getElementById("balance-value").textContent = stats.formatted_balance;
  document.getElementById("month-income").textContent = stats.formatted_month_income;
  document.getElementById("month-expense").textContent = stats.formatted_month_expense;

  // Statistics Panel
  document.getElementById("stat-today-exp").textContent = stats.formatted_today_expense;
  document.getElementById("stat-week-exp").textContent = stats.formatted_week_expense;
  document.getElementById("stat-month-exp").textContent = stats.formatted_month_expense;
  document.getElementById("stat-total-inc").textContent = stats.formatted_total_income;
  document.getElementById("stat-month-card").textContent =
    stats.formatted_month_card_expense || "− €0.00";
  document.getElementById("stat-month-cash").textContent =
    stats.formatted_month_cash_expense || "− €0.00";
  document.getElementById("stat-net-diff").textContent = stats.formatted_net_diff;
  document.getElementById("stat-balance").textContent = stats.formatted_balance;

  // History Panel
  document.getElementById("history-count").textContent = `${transactions.length}`;
  const histContainer = document.getElementById("history-list");
  histContainer.innerHTML = "";
  if (transactions.length === 0) {
    histContainer.innerHTML = `<div class="tx-meta">${dict.empty_history}</div>`;
  } else {
    transactions.forEach((tx) => {
      const row = document.createElement("div");
      row.className = "tx-row";
      const catLabel = tx.category_label || "";
      const desc = tx.description
        ? `${tx.description} (${catLabel})`
        : catLabel || (tx.tx_type === "income" ? "Income" : "Expense");
      const payIcon = tx.payment_method === "cash" ? "💵" : "💳";
      const nextPay = tx.payment_method === "cash" ? "card" : "cash";
      row.innerHTML = `
        <div class="tx-info">
          <div class="tx-desc">${escapeHtml(desc)}</div>
          <div class="tx-meta">${tx.date} • ${tx.time} • ${tx.currency}</div>
        </div>
        <div class="tx-right">
          <span class="tx-amt ${tx.tx_type}">${tx.formatted_amount}</span>
          <button class="icon-btn" title="Cash / Card" onclick="togglePaymentMethod(${tx.id}, '${nextPay}')">${payIcon}</button>
          <button class="icon-btn" onclick="openEditTxModal(${tx.id})">✏️</button>
          <button class="icon-btn" onclick="deleteTx(${tx.id})">🗑</button>
        </div>
      `;
      histContainer.appendChild(row);
    });
  }

  // Recurring Panel
  const recContainer = document.getElementById("recurring-list");
  recContainer.innerHTML = "";
  if (recurring.length === 0) {
    recContainer.innerHTML = `<div class="tx-meta">${dict.empty_recurring}</div>`;
  } else {
    recurring.forEach((rec) => {
      const row = document.createElement("div");
      row.className = "tx-row";
      const statusBadge = rec.is_active ? "✅" : "⏸";
      row.innerHTML = `
        <div class="tx-info">
          <div class="tx-desc">${statusBadge} ${escapeHtml(rec.title)}</div>
          <div class="tx-meta">${rec.period} • Next: ${rec.next_date_formatted}</div>
        </div>
        <div class="tx-right">
          <span class="tx-amt ${rec.tx_type}">${rec.formatted_amount}</span>
          <button class="icon-btn" onclick="toggleRecurring(${rec.id})">⏯</button>
          <button class="icon-btn" onclick="deleteRecurring(${rec.id})">🗑</button>
        </div>
      `;
      recContainer.appendChild(row);
    });
  }

  // Partner Panel
  if (partner_info) {
    document.getElementById("my-partner-code").textContent =
      partner_info.partner_code || "—";
    const unlinkedBox = document.getElementById("partner-unlinked-box");
    const linkedBox = document.getElementById("partner-linked-box");
    if (partner_info.is_linked && partner_info.partner) {
      unlinkedBox.classList.add("hidden");
      linkedBox.classList.remove("hidden");
      const p = partner_info.partner;
      document.getElementById("partner-name-val").textContent = p.name;
      document.getElementById("partner-balance-val").textContent = p.formatted_balance;
      document.getElementById("partner-inc-val").textContent = p.formatted_month_income;
      document.getElementById("partner-exp-val").textContent = p.formatted_month_expense;
      document.getElementById("partner-card-val").textContent = p.formatted_month_card;
      document.getElementById("partner-cash-val").textContent = p.formatted_month_cash;

      const pHist = document.getElementById("partner-history-list");
      pHist.innerHTML = "";
      if (!p.transactions || p.transactions.length === 0) {
        pHist.innerHTML = `<div class="tx-meta">${dict.empty_history}</div>`;
      } else {
        p.transactions.forEach((tx) => {
          const row = document.createElement("div");
          row.className = "tx-row";
          const catLabel = tx.category_label || "";
          const desc = tx.description
            ? `${tx.description} (${catLabel})`
            : catLabel;
          const payIcon = tx.payment_method === "cash" ? "💵" : "💳";
          row.innerHTML = `
            <div class="tx-info">
              <div class="tx-desc">${payIcon} ${escapeHtml(desc)}</div>
              <div class="tx-meta">${tx.date} • ${tx.time} • ${tx.currency}</div>
            </div>
            <div class="tx-right">
              <span class="tx-amt ${tx.tx_type}">${tx.formatted_amount}</span>
            </div>
          `;
          pHist.appendChild(row);
        });
      }
    } else {
      unlinkedBox.classList.remove("hidden");
      linkedBox.classList.add("hidden");
    }
  }

  // Profile Panel
  if (catalog) {
    const countrySelect = document.getElementById("prof-country");
    countrySelect.innerHTML = catalog.countries
      .map((c) => {
        const cName =
          appState.lang === "de"
            ? c.name_de || c.name_en
            : appState.lang === "en"
            ? c.name_en
            : c.name_ru;
        return `<option value="${c.code}" ${
          c.code === user.country_code ? "selected" : ""
        }>${c.flag} ${cName}</option>`;
      })
      .join("");

    const curSelect = document.getElementById("prof-currency");
    curSelect.innerHTML = catalog.currencies
      .map(
        (c) =>
          `<option value="${c.code}" ${c.code === user.currency ? "selected" : ""}>${c.code} — ${
            appState.lang === "ru" ? c.name_ru : c.name_en
          } (${c.symbol})</option>`
      )
      .join("");

    const tzSelect = document.getElementById("prof-timezone");
    const tzList = catalog.timezones.includes(user.timezone)
      ? catalog.timezones
      : [user.timezone, ...catalog.timezones];
    tzSelect.innerHTML = tzList
      .map((tz) => `<option value="${tz}" ${tz === user.timezone ? "selected" : ""}>${tz}</option>`)
      .join("");
  }

  document.getElementById("prof-name").value = user.name || "";
  document.getElementById("prof-phone").value = user.phone || "";
  document.getElementById("prof-language").value = normalizeLang(user.language || "ru");
  document.getElementById("prof-notify-rec").checked = Boolean(user.notify_recurring);
  document.getElementById("prof-daily-rem").checked = Boolean(user.daily_reminder);
  document.getElementById("prof-reg-date").textContent = user.registered_date || "—";
}

function switchPanel(panelName) {
  ["stats", "history", "recurring", "partner", "profile"].forEach((name) => {
    const el = document.getElementById(`panel-${name}`);
    const btn = document.getElementById(`tab-btn-${name}`);
    if (el) {
      if (name === panelName) el.classList.remove("hidden");
      else el.classList.add("hidden");
    }
    if (btn) {
      if (name === panelName) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  });
}

function openTxModal(txType) {
  const dict = I18N[appState.lang];
  document.getElementById("tx-modal-id").value = "";
  document.getElementById("tx-modal-type").value = txType;
  document.getElementById("tx-modal-amount").value = "";
  document.getElementById("tx-modal-desc").value = "";
  document.getElementById("tx-modal-payment").value = "card";
  document.getElementById("tx-modal-title").textContent =
    txType === "income" ? dict.btn_add_income : dict.btn_add_expense;
  document.getElementById("tx-modal").classList.remove("hidden");
  document.getElementById("tx-modal-amount").focus();
}

function openEditTxModal(txId) {
  const tx = appState.transactions.find((item) => item.id === txId);
  if (!tx) return;
  document.getElementById("tx-modal-id").value = String(tx.id);
  document.getElementById("tx-modal-type").value = tx.tx_type;
  document.getElementById("tx-modal-amount").value = String(tx.amount);
  document.getElementById("tx-modal-desc").value = tx.description || "";
  document.getElementById("tx-modal-payment").value = tx.payment_method || "card";
  document.getElementById("tx-modal-title").textContent = `✏️ #${tx.id}`;
  document.getElementById("tx-modal").classList.remove("hidden");
}

function closeTxModal() {
  document.getElementById("tx-modal").classList.add("hidden");
}

async function togglePaymentMethod(txId, newMethod) {
  await fetch(`/api/transactions/${txId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify({ payment_method: newMethod }),
  });
  await fetchDashboard();
}

function openRecurringModal() {
  document.getElementById("rec-title").value = "";
  document.getElementById("rec-amount").value = "";
  document.getElementById("rec-date").value = new Date().toISOString().slice(0, 10);
  document.getElementById("rec-modal").classList.remove("hidden");
}

function closeRecurringModal() {
  document.getElementById("rec-modal").classList.add("hidden");
}

// Quick 2-second entry bar submit
document.getElementById("quick-entry-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("quick-input");
  const raw = input.value.trim();
  if (!raw) return;

  const res = await fetch("/api/transactions", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ quick_text: raw }),
  });

  if (res.ok) {
    const data = await res.json();
    const tx = data.transaction;
    const dict = I18N[appState.lang];
    const header = tx.tx_type === "income" ? dict.saved_income : dict.saved_expense;
    showToast(
      `<strong>✅ ${header}</strong><br/>${tx.formatted_amount} ${
        tx.description ? "— " + escapeHtml(tx.description) : ""
      }<br/>💼 ${tx.formatted_balance}`
    );
    input.value = "";
    await fetchDashboard();
  }
});

// Modal Add / Edit Transaction submit
document.getElementById("tx-modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const txId = document.getElementById("tx-modal-id").value;
  const txType = document.getElementById("tx-modal-type").value;
  const amount = document.getElementById("tx-modal-amount").value;
  const description = document.getElementById("tx-modal-desc").value;
  const payment_method = document.getElementById("tx-modal-payment").value;

  if (txId) {
    await fetch(`/api/transactions/${txId}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ tx_type: txType, amount, description, payment_method }),
    });
  } else {
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ tx_type: txType, amount, description, payment_method }),
    });
    if (res.ok) {
      const data = await res.json();
      const tx = data.transaction;
      const dict = I18N[appState.lang];
      const header = tx.tx_type === "income" ? dict.saved_income : dict.saved_expense;
      showToast(
        `<strong>✅ ${header}</strong><br/>${tx.formatted_amount} ${
          tx.description ? "— " + escapeHtml(tx.description) : ""
        }<br/>💼 ${tx.formatted_balance}`
      );
    }
  }
  closeTxModal();
  await fetchDashboard();
});

async function deleteTx(txId) {
  await fetch(`/api/transactions/${txId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  await fetchDashboard();
}

// Partner link form submit
document.getElementById("partner-link-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const codeInput = document.getElementById("partner-code-input");
  const partner_code = codeInput.value.trim();
  if (!partner_code) return;

  const res = await fetch("/api/partner/link", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ partner_code }),
  });
  if (res.ok) {
    codeInput.value = "";
    showToast("🤝 Аккаунты успешно связаны!");
    await fetchDashboard();
  } else {
    showToast("⚠️ Проверьте код партнёра");
  }
});

// Recurring Modal submit
document.getElementById("rec-modal-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    tx_type: document.getElementById("rec-type").value,
    title: document.getElementById("rec-title").value,
    amount: document.getElementById("rec-amount").value,
    period: document.getElementById("rec-period").value,
    next_run_date: document.getElementById("rec-date").value,
  };
  await fetch("/api/recurring", {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  closeRecurringModal();
  await fetchDashboard();
});

async function toggleRecurring(recId) {
  await fetch(`/api/recurring/${recId}/toggle`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  await fetchDashboard();
}

async function deleteRecurring(recId) {
  await fetch(`/api/recurring/${recId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  await fetchDashboard();
}

// Profile form submit
document.getElementById("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById("prof-name").value,
    phone: document.getElementById("prof-phone").value,
    country_code: document.getElementById("prof-country").value,
    currency: document.getElementById("prof-currency").value,
    timezone: document.getElementById("prof-timezone").value,
    language: document.getElementById("prof-language").value,
    notify_recurring: document.getElementById("prof-notify-rec").checked,
    daily_reminder: document.getElementById("prof-daily-rem").checked,
  };
  await fetch("/api/profile", {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  showToast("✅ Настройки сохранены / Settings saved");
  await fetchDashboard();
});

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

fetchDashboard();
