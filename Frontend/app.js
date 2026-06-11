const API_URL = "/api";

const state = {
    instruments: [],
    activeLoans: [],
    overdueLoans: [],
    dashboard: null,
    reports: null,
    selectedLoan: null,
};

const money = (value) => `Rs ${Number(value || 0).toFixed(2)}`;
const today = () => new Date().toISOString().slice(0, 10);
const byId = (id) => document.getElementById(id);

function showNotice(message, type = "success") {
    const notice = byId("notice");
    notice.textContent = message;
    notice.className = `notice ${type}`;
    notice.hidden = false;
    window.setTimeout(() => {
        notice.hidden = true;
    }, 3600);
}

async function api(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || "Request failed");
    }
    return data;
}

function badge(status) {
    return `<span class="status-badge ${status.toLowerCase().replaceAll(" ", "-")}">${status}</span>`;
}

function empty(message) {
    return `<div class="empty-state">${message}</div>`;
}

function setView(viewId) {
    document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === viewId));
    document.querySelectorAll(".nav-btn").forEach((btn) => btn.classList.toggle("active", btn.dataset.view === viewId));
}

function openModal(id) {
    const modal = byId(id);
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
}

function closeModals() {
    document.querySelectorAll(".modal").forEach((modal) => {
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
    });
}

async function loadHealth() {
    try {
        const response = await fetch("/health");
        const data = await response.json();
        byId("healthStatus").textContent = data.status === "ok" ? "Server online" : "Server issue";
        byId("healthStatus").classList.add("online");
    } catch {
        byId("healthStatus").textContent = "Server offline";
        byId("healthStatus").classList.add("offline");
    }
}

async function loadDashboard() {
    state.dashboard = await api("/dashboard");
    const metrics = [
        ["Total Instruments", state.dashboard.total_instruments],
        ["Available", state.dashboard.available],
        ["On Loan", state.dashboard.on_loan],
        ["Under Repair", state.dashboard.under_repair],
        ["Overdue Loans", state.dashboard.overdue_loans],
        ["This Month Deposits", money(state.dashboard.month_deposits)],
    ];
    byId("metricGrid").innerHTML = metrics.map(([label, value]) => `
        <article class="metric-card">
            <span>${label}</span>
            <strong>${value}</strong>
        </article>
    `).join("");

    const total = Math.max(state.dashboard.total_instruments, 1);
    byId("statusBars").innerHTML = Object.entries(state.dashboard.status_counts).map(([label, count]) => `
        <div class="bar-row">
            <div class="bar-label"><span>${label}</span><strong>${count}</strong></div>
            <div class="bar-track"><span style="width:${(count / total) * 100}%"></span></div>
        </div>
    `).join("");
}

async function loadInstruments() {
    const status = byId("statusFilter")?.value || "";
    state.instruments = await api(`/instruments${status ? `?status=${encodeURIComponent(status)}` : ""}`);
    byId("inventoryBody").innerHTML = state.instruments.length ? state.instruments.map((inst) => `
        <tr>
            <td><strong>${inst.type}</strong></td>
            <td>${inst.brand}</td>
            <td>${inst.serial_no}</td>
            <td>${inst.condition}</td>
            <td>${badge(inst.status)}</td>
            <td class="actions-cell">
                <button class="text-btn" data-edit-instrument="${inst.id}">Edit</button>
                <button class="text-btn" data-loan-instrument="${inst.id}" ${inst.status !== "Available" ? "disabled" : ""}>Loan</button>
                <button class="text-btn danger" data-delete-instrument="${inst.id}" ${inst.active_loan_id ? "disabled" : ""}>Delete</button>
            </td>
        </tr>
    `).join("") : `<tr><td colspan="6">${empty("No instruments match this filter.")}</td></tr>`;
}

async function loadLoans() {
    state.activeLoans = await api("/loans?status=active");
    byId("activeLoansList").innerHTML = state.activeLoans.length ? state.activeLoans.map(loanCard).join("") : empty("No active loans. Instruments returned here will appear in reports.");
}

async function loadOverdue() {
    state.overdueLoans = await api("/overdue");
    byId("overdueList").innerHTML = state.overdueLoans.length ? state.overdueLoans.map(loanCard).join("") : empty("No overdue loans today.");
    byId("dashboardOverdue").innerHTML = state.overdueLoans.length
        ? state.overdueLoans.slice(0, 3).map((loan) => `
            <div class="mini-alert">
                <strong>${loan.student_name}</strong>
                <span>${loan.instrument.type} overdue by ${loan.days_overdue} day(s)</span>
            </div>
        `).join("")
        : empty("No recovery action needed.");
}

function loanCard(loan) {
    const overdueText = loan.days_overdue > 0 ? `<span class="overdue-text">${loan.days_overdue} day(s) overdue</span>` : `<span>Due ${loan.expected_return_date}</span>`;
    return `
        <article class="loan-card">
            <div>
                <p class="eyebrow">${loan.instrument.type} - ${loan.instrument.brand}</p>
                <h3>${loan.student_name}</h3>
                <p>${loan.student_phone}</p>
            </div>
            <div>
                <span>Deposit</span>
                <strong>${money(loan.deposit_collected)}</strong>
            </div>
            <div>
                <span>Loan Date</span>
                <strong>${loan.loan_date}</strong>
            </div>
            <div>
                ${overdueText}
                <strong>${loan.expected_return_date}</strong>
            </div>
            <button class="primary-btn" data-return-loan="${loan.id}">Record Return</button>
        </article>
    `;
}

async function loadReports() {
    const start = byId("reportStart").value;
    const end = byId("reportEnd").value;
    const params = new URLSearchParams();
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    state.reports = await api(`/reports/summary${params.toString() ? `?${params}` : ""}`);

    const metrics = [
        ["Loans", state.reports.loan_count],
        ["Returned", state.reports.returned_count],
        ["Deposits", money(state.reports.deposit_total)],
        ["Deductions", money(state.reports.deduction_total)],
        ["Refunds", money(state.reports.refund_total)],
    ];
    byId("reportMetrics").innerHTML = metrics.map(([label, value]) => `
        <article class="metric-card">
            <span>${label}</span>
            <strong>${value}</strong>
        </article>
    `).join("");

    const max = Math.max(...state.reports.monthly_deposits.map((item) => item.amount), 1);
    byId("depositChart").innerHTML = state.reports.monthly_deposits.length ? state.reports.monthly_deposits.map((item) => `
        <div class="chart-row">
            <span>${item.month}</span>
            <div class="chart-track"><strong style="width:${(item.amount / max) * 100}%">${money(item.amount)}</strong></div>
        </div>
    `).join("") : empty("No deposits found for this date range.");
}

async function refreshAll() {
    try {
        await Promise.all([loadDashboard(), loadInstruments(), loadLoans(), loadOverdue(), loadReports()]);
    } catch (error) {
        showNotice(error.message, "error");
    }
}

function fillInstrumentForm(inst = null) {
    byId("instrumentModalTitle").textContent = inst ? "Edit Instrument" : "Add Instrument";
    byId("instrumentId").value = inst?.id || "";
    byId("instrumentType").value = inst?.type || "";
    byId("instrumentBrand").value = inst?.brand || "";
    byId("instrumentSerial").value = inst?.serial_no || "";
    byId("instrumentCondition").value = inst?.condition || "Excellent";
    byId("instrumentStatus").value = inst?.status || "Available";
    byId("instrumentNotes").value = inst?.notes || "";
}

function startLoan(inst) {
    byId("loanInstrumentId").value = inst.id;
    byId("selectedInstrument").textContent = `${inst.type} - ${inst.brand} (${inst.serial_no})`;
    byId("loanDate").value = today();
    byId("expectedReturnDate").value = "";
    byId("loanForm").reset();
    byId("loanInstrumentId").value = inst.id;
    byId("selectedInstrument").textContent = `${inst.type} - ${inst.brand} (${inst.serial_no})`;
    byId("loanDate").value = today();
    openModal("loanModal");
}

function startReturn(loan) {
    state.selectedLoan = loan;
    byId("returnLoanId").value = loan.id;
    byId("selectedLoan").textContent = `${loan.student_name} returning ${loan.instrument.type} - deposit ${money(loan.deposit_collected)}`;
    byId("actualReturnDate").value = today();
    byId("damageDeduction").value = "0";
    byId("conditionAtReturn").value = "";
    byId("damageNotes").value = "";
    byId("returnInstrumentStatus").value = "Available";
    updateRefundPreview();
    openModal("returnModal");
}

function updateRefundPreview() {
    const loan = state.selectedLoan;
    const deduction = Number(byId("damageDeduction").value || 0);
    const refund = Math.max(Number(loan?.deposit_collected || 0) - deduction, 0);
    byId("refundPreview").textContent = money(refund);
}

function exportCsv() {
    const rows = [["Metric", "Value"], ["Loans", state.reports.loan_count], ["Returned", state.reports.returned_count], ["Deposits", state.reports.deposit_total], ["Deductions", state.reports.deduction_total], ["Refunds", state.reports.refund_total]];
    const csv = rows.map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "student-instrument-report.csv";
    link.click();
    URL.revokeObjectURL(link.href);
}

document.addEventListener("click", async (event) => {
    const target = event.target;
    if (target.matches(".nav-btn")) setView(target.dataset.view);
    if (target.dataset.viewLink) setView(target.dataset.viewLink);
    if (target.dataset.open) {
        fillInstrumentForm();
        openModal(target.dataset.open);
    }
    if (target.dataset.close !== undefined || target.classList.contains("modal")) closeModals();

    if (target.dataset.editInstrument) {
        const inst = state.instruments.find((item) => item.id === Number(target.dataset.editInstrument));
        fillInstrumentForm(inst);
        openModal("instrumentModal");
    }

    if (target.dataset.loanInstrument) {
        const inst = state.instruments.find((item) => item.id === Number(target.dataset.loanInstrument));
        startLoan(inst);
    }

    if (target.dataset.returnLoan) {
        const loan = state.activeLoans.find((item) => item.id === Number(target.dataset.returnLoan)) || state.overdueLoans.find((item) => item.id === Number(target.dataset.returnLoan));
        startReturn(loan);
    }

    if (target.dataset.deleteInstrument) {
        if (!confirm("Delete this instrument record?")) return;
        try {
            await api(`/instruments/${target.dataset.deleteInstrument}`, { method: "DELETE" });
            showNotice("Instrument deleted.");
            refreshAll();
        } catch (error) {
            showNotice(error.message, "error");
        }
    }
});

byId("instrumentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = byId("instrumentId").value;
    const payload = {
        type: byId("instrumentType").value,
        brand: byId("instrumentBrand").value,
        serial_no: byId("instrumentSerial").value,
        condition: byId("instrumentCondition").value,
        status: byId("instrumentStatus").value,
        notes: byId("instrumentNotes").value,
    };
    try {
        await api(id ? `/instruments/${id}` : "/instruments", { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
        closeModals();
        showNotice(id ? "Instrument updated." : "Instrument added.");
        refreshAll();
    } catch (error) {
        showNotice(error.message, "error");
    }
});

byId("loanForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
        instrument_id: Number(byId("loanInstrumentId").value),
        student_name: byId("studentName").value,
        student_phone: byId("studentPhone").value,
        loan_date: byId("loanDate").value,
        expected_return_date: byId("expectedReturnDate").value,
        deposit_collected: byId("depositCollected").value,
        condition_at_loan: byId("conditionAtLoan").value,
        condition_photo_url: byId("conditionPhotoUrl").value,
    };
    try {
        await api("/loans", { method: "POST", body: JSON.stringify(payload) });
        closeModals();
        showNotice("Loan created and instrument marked On Loan.");
        refreshAll();
    } catch (error) {
        showNotice(error.message, "error");
    }
});

byId("returnForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
        return_date: byId("actualReturnDate").value,
        condition_at_return: byId("conditionAtReturn").value,
        damage_notes: byId("damageNotes").value,
        damage_deduction: byId("damageDeduction").value,
        instrument_status: byId("returnInstrumentStatus").value,
    };
    try {
        await api(`/loans/${byId("returnLoanId").value}/return`, { method: "PATCH", body: JSON.stringify(payload) });
        closeModals();
        showNotice("Return recorded and refund calculated.");
        refreshAll();
    } catch (error) {
        showNotice(error.message, "error");
    }
});

byId("statusFilter").addEventListener("change", loadInstruments);
byId("reportStart").addEventListener("change", loadReports);
byId("reportEnd").addEventListener("change", loadReports);
byId("damageDeduction").addEventListener("input", updateRefundPreview);
byId("exportCsvBtn").addEventListener("click", exportCsv);

loadHealth();
refreshAll();
