/* Personal Finance Bot — Telegram Mini App Frontend */

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
    btn_recurring: "Регулярные операции",
    btn_profile: "Мой профиль и настройки",
    stats_title: "📊 Финансовая статистика",
    stat_today_exp: "Расходы за день",
    stat_week_exp: "Расходы за неделю",
    stat_month_exp: "Расходы за месяц",
    stat_total_inc: "Общие доходы",
    stat_net_diff: "Разница (доходы − расходы)",
    history_title: "🕒 История операций",
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
    lbl_desc: "Описание (необязательно)",
    btn_save: "Сохранить",
    add_rec_title: "Новая регулярная операция",
    lbl_type: "Тип операции",
    lbl_title: "Название",
    lbl_period: "Периодичность",
    lbl_next_date: "Дата следующего списания/начисления",
    quick_placeholder: "Быстрый ввод: 5 Обед, 12.50, +1500 Зарплата...",
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
    btn_recurring: "Recurring Operations",
    btn_profile: "My Profile & Settings",
    stats_title: "📊 Financial Statistics",
    stat_today_exp: "Today's Expenses",
    stat_week_exp: "Weekly Expenses",
    stat_month_exp: "Monthly Expenses",
    stat_total_inc: "Total Income",
    stat_net_diff: "Net Difference (income − expenses)",
    history_title: "🕒 Transaction History",
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
    lbl_desc: "Description (optional)",
    btn_save: "Save",
    add_rec_title: "New Recurring Operation",
    lbl_type: "Operation Type",
    lbl_title: "Title",
    lbl_period: "Frequency",
    lbl_next_date: "Next Execution Date",
    quick_placeholder: "Quick entry: 5 Lunch, 12.50, +1500 Salary...",
    empty_history: "No transactions yet. Enter an amount above!",
    empty_recurring: "No recurring operations yet.",
    saved_expense: "Expense Saved • Success",
    saved_income: "Income Saved • Success",
  },
};

let appState = {
  lang: "ru",
  user: null,
  stats: null,
  transactions: [],
  recurring: [],
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

function applyLanguage(lang) {
  appState.lang = lang === "en" ? "en" : "ru";
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
  appState.catalog = data.catalog;

  applyLanguage(data.user.language);
  renderDashboard();
}

function renderDashboard() {
  const { user, stats, transactions, recurring, catalog } = appState;
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
      const desc = tx.description || (tx.tx_type === "income" ? "Доход / Income" : "Расход / Expense");
      row.innerHTML = `
        <div class="tx-info">
          <div class="tx-desc">${escapeHtml(desc)}</div>
          <div class="tx-meta">${tx.date} • ${tx.time} • ${tx.currency}</div>
        </div>
        <div class="tx-right">
          <span class="tx-amt ${tx.tx_type}">${tx.formatted_amount}</span>
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

  // Profile Panel
  if (catalog) {
    const countrySelect = document.getElementById("prof-country");
    countrySelect.innerHTML = catalog.countries
      .map(
        (c) =>
          `<option value="${c.code}" ${c.code === user.country_code ? "selected" : ""}>${c.flag} ${
            appState.lang === "en" ? c.name_en : c.name_ru
          }</option>`
      )
      .join("");

    const curSelect = document.getElementById("prof-currency");
    curSelect.innerHTML = catalog.currencies
      .map(
        (c) =>
          `<option value="${c.code}" ${c.code === user.currency ? "selected" : ""}>${c.code} — ${
            appState.lang === "en" ? c.name_en : c.name_ru
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
  document.getElementById("prof-language").value = user.language || "ru";
  document.getElementById("prof-notify-rec").checked = Boolean(user.notify_recurring);
  document.getElementById("prof-daily-rem").checked = Boolean(user.daily_reminder);
  document.getElementById("prof-reg-date").textContent = user.registered_date || "—";
}

function switchPanel(panelName) {
  ["stats", "history", "recurring", "profile"].forEach((name) => {
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
  document.getElementById("tx-modal-title").textContent = `✏️ #${tx.id}`;
  document.getElementById("tx-modal").classList.remove("hidden");
}

function closeTxModal() {
  document.getElementById("tx-modal").classList.add("hidden");
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

  if (txId) {
    await fetch(`/api/transactions/${txId}`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ tx_type: txType, amount, description }),
    });
  } else {
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ tx_type: txType, amount, description }),
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

