/**
 * main.js — Interatividade completa da aplicação.
 * Features: Modal, CSRF, Dark mode, Filtros, CSV Export, Simulador, Chart, Toast.
 * Segurança: sem eval(), sem innerHTML com dados do usuário, inputs sanitizados.
 */

"use strict";

// ---------------------------------------------------------------------------
// Constantes
// ---------------------------------------------------------------------------
const API_BASE   = "/api/dividas";
const $          = (id) => document.getElementById(id);
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") ?? "";

// Categoria → cor (deve espelhar o CSS)
const CAT_COLORS = {
    "Cartão de Crédito": "#007AFF",
    "Empréstimo":        "#FF9500",
    "Financiamento":     "#AF52DE",
    "Aluguel":           "#FF2D55",
    "Saúde":            "#34C759",
    "Educação":         "#5856D6",
    "Outro":            "#8E8E93",
};

// ---------------------------------------------------------------------------
// CSRF Fetch Wrapper
// ---------------------------------------------------------------------------
async function apiFetch(url, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        "X-CSRF-Token": CSRF_TOKEN,
        ...(options.headers || {}),
    };
    return fetch(url, { ...options, headers });
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
const toastEl = $("toast");

function showToast(msg, tipo = "default") {
    toastEl.textContent = msg;
    toastEl.className = `toast is-visible${tipo !== "default" ? ` toast--${tipo}` : ""}`;
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(() => { toastEl.className = "toast"; }, 3400);
}

// ---------------------------------------------------------------------------
// Dark Mode
// ---------------------------------------------------------------------------
const HTML      = document.documentElement;
const darkBtn   = $("dark-toggle");
const DARK_KEY  = "debt-tracker-theme";

function applyTheme(dark) {
    HTML.setAttribute("data-theme", dark ? "dark" : "light");
    if (darkBtn) darkBtn.textContent = dark ? "☀️" : "🌙";
    localStorage.setItem(DARK_KEY, dark ? "dark" : "light");
}

// Inicializa com preferência salva ou sistema
const savedTheme = localStorage.getItem(DARK_KEY);
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
applyTheme(savedTheme ? savedTheme === "dark" : prefersDark);

darkBtn?.addEventListener("click", () => {
    applyTheme(HTML.getAttribute("data-theme") !== "dark");
});

// ---------------------------------------------------------------------------
// Modal: Nova Dívida
// ---------------------------------------------------------------------------
const modalOverlay   = $("modal-overlay");
const modalConfirmar = $("modal-confirmar");
const modalSimulador = $("modal-simulador");
const formNovaDivida = $("form-nova-divida");

function resetFormErrors() {
    ["nome", "valor-total", "total-parcelas"].forEach((campo) => {
        const input = $(`input-${campo}`);
        const erro  = $(`erro-${campo}`);
        if (input) input.classList.remove("is-invalid");
        if (erro)  erro.textContent = "";
    });
    const prev = $("parcela-preview");
    if (prev) prev.style.display = "none";
}

function setFieldError(campo, msg) {
    const input = $(`input-${campo}`);
    const erro  = $(`erro-${campo}`);
    if (input) input.classList.add("is-invalid");
    if (erro)  erro.textContent = msg;
}

function abrirModal() {
    modalOverlay.classList.add("is-active");
    document.body.style.overflow = "hidden";
    setTimeout(() => $("input-nome")?.focus(), 60);
}

function fecharModal() {
    modalOverlay.classList.remove("is-active");
    document.body.style.overflow = "";
    formNovaDivida.reset();
    resetFormErrors();
}

function fecharModalConfirmar() {
    modalConfirmar?.classList.remove("is-active");
    document.body.style.overflow = "";
}

function fecharModalSimulador() {
    modalSimulador?.classList.remove("is-active");
    document.body.style.overflow = "";
}

["btn-abrir-modal", "btn-abrir-modal-2", "btn-abrir-modal-3"].forEach((id) => {
    $$(id)?.addEventListener("click", abrirModal);
});

function $$(id) { return document.getElementById(id); }

["btn-abrir-modal", "btn-abrir-modal-2", "btn-abrir-modal-3"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", abrirModal);
});

$("btn-fechar-modal")?.addEventListener("click", fecharModal);
$("btn-cancelar")?.addEventListener("click", fecharModal);
$("btn-fechar-simulador")?.addEventListener("click", fecharModalSimulador);
$("btn-cancelar-simulador")?.addEventListener("click", fecharModalSimulador);

modalOverlay?.addEventListener("click", (e) => { if (e.target === modalOverlay) fecharModal(); });
modalConfirmar?.addEventListener("click", (e) => { if (e.target === modalConfirmar) fecharModalConfirmar(); });
modalSimulador?.addEventListener("click", (e) => { if (e.target === modalSimulador) fecharModalSimulador(); });

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { fecharModal(); fecharModalConfirmar(); fecharModalSimulador(); }
});

// ---------------------------------------------------------------------------
// Preview: Parcela Calculada em Tempo Real
// ---------------------------------------------------------------------------
function atualizarPreviewParcela() {
    const valorTotal    = parseFloat($("input-valor-total")?.value);
    const totalParcelas = parseInt($("input-total-parcelas")?.value, 10);
    const preview       = $("parcela-preview");
    const previewValor  = $("parcela-preview-valor");

    if (valorTotal > 0 && totalParcelas >= 1 && preview && previewValor) {
        const parcela = valorTotal / totalParcelas;
        previewValor.textContent = `R$ ${parcela.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        preview.style.display = "block";
        // Adjust preview to full width inside form-grid
        preview.style.gridColumn = "1 / -1";
    } else if (preview) {
        preview.style.display = "none";
    }
}

$("input-valor-total")?.addEventListener("input", atualizarPreviewParcela);
$("input-total-parcelas")?.addEventListener("input", atualizarPreviewParcela);

// ---------------------------------------------------------------------------
// Formulário: Criar Nova Dívida
// ---------------------------------------------------------------------------
formNovaDivida?.addEventListener("submit", async (e) => {
    e.preventDefault();
    resetFormErrors();

    const nome           = $("input-nome")?.value.trim();
    const categoria      = $("input-categoria")?.value;
    const valor_total    = parseFloat($("input-valor-total")?.value);
    const total_parcelas = parseInt($("input-total-parcelas")?.value, 10);
    const dia_vencimento = $("input-dia-vencimento")?.value ? parseInt($("input-dia-vencimento").value, 10) : null;

    let valido = true;
    if (!nome) { setFieldError("nome", "O nome da dívida é obrigatório."); valido = false; }
    if (!valor_total || valor_total <= 0) { setFieldError("valor-total", "Informe um valor total positivo."); valido = false; }
    if (!total_parcelas || total_parcelas < 1) { setFieldError("total-parcelas", "Informe pelo menos 1 parcela."); valido = false; }
    if (!valido) return;

    const btnSubmit = $("btn-submit");
    btnSubmit.textContent = "Salvando…";
    btnSubmit.disabled = true;

    try {
        const payload = { nome, categoria, valor_total, total_parcelas };
        if (dia_vencimento) payload.dia_vencimento = dia_vencimento;

        const res  = await apiFetch(API_BASE, { method: "POST", body: JSON.stringify(payload) });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.erro || "Erro ao salvar dívida.", "error");
        } else {
            showToast("Dívida cadastrada com sucesso!", "success");
            fecharModal();
            setTimeout(() => location.reload(), 800);
        }
    } catch (err) {
        showToast("Falha de conexão com o servidor.", "error");
        console.error(err);
    } finally {
        btnSubmit.textContent = "Salvar Dívida";
        btnSubmit.disabled = false;
    }
});

// ---------------------------------------------------------------------------
// Pagar Parcela
// ---------------------------------------------------------------------------
async function pagarParcela(dividaId) {
    const btn = $(`btn-pagar-${dividaId}`);
    if (btn) { btn.textContent = "Pagando…"; btn.disabled = true; }

    try {
        const res  = await apiFetch(`${API_BASE}/${dividaId}/pagar`, { method: "PUT", body: JSON.stringify({ quantidade: 1 }) });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.erro || "Erro ao registrar pagamento.", "error");
            if (btn) { btn.textContent = "Pagar Parcela"; btn.disabled = false; }
        } else {
            showToast(data.esta_quitada ? "🎉 Dívida quitada!" : "Parcela registrada!", "success");
            setTimeout(() => location.reload(), 800);
        }
    } catch (err) {
        showToast("Falha de conexão com o servidor.", "error");
        if (btn) { btn.textContent = "Pagar Parcela"; btn.disabled = false; }
    }
}

// ---------------------------------------------------------------------------
// Excluir Dívida
// ---------------------------------------------------------------------------
let _pendingDeleteId = null;

function confirmarExclusao(dividaId, nome) {
    _pendingDeleteId = dividaId;
    const nomeEl = $("nome-confirmar");
    if (nomeEl) nomeEl.textContent = `"${nome}"`;
    modalConfirmar?.classList.add("is-active");
    document.body.style.overflow = "hidden";
}

$("btn-confirmar-excluir")?.addEventListener("click", async () => {
    if (!_pendingDeleteId) return;
    const dividaId = _pendingDeleteId;
    _pendingDeleteId = null;
    fecharModalConfirmar();

    try {
        const res = await apiFetch(`${API_BASE}/${dividaId}`, { method: "DELETE" });
        if (res.ok) {
            showToast("Dívida excluída.", "success");
            const card = $(`card-${dividaId}`);
            if (card) {
                card.style.transition = "opacity 0.3s, transform 0.3s";
                card.style.opacity = "0";
                card.style.transform = "scale(0.94)";
            }
            setTimeout(() => location.reload(), 600);
        } else {
            const data = await res.json();
            showToast(data.erro || "Erro ao excluir dívida.", "error");
        }
    } catch (err) {
        showToast("Falha de conexão com o servidor.", "error");
    }
});

// ---------------------------------------------------------------------------
// Filtros em Tempo Real
// ---------------------------------------------------------------------------
const filtrosBusca     = $("filtro-busca");
const filtrosCategoria = $("filtro-categoria");
const filtroPills      = document.querySelectorAll(".filter-pill");
let   filtroStatus     = "todos";

function aplicarFiltros() {
    const busca    = filtrosBusca?.value.toLowerCase().trim() ?? "";
    const categoria = filtrosCategoria?.value ?? "";
    const cards    = document.querySelectorAll(".divida-card");
    let   visiveis = 0;

    cards.forEach((card) => {
        const nome     = card.dataset.nome ?? "";
        const cat      = card.dataset.cat  ?? "";
        const status   = card.dataset.status ?? "";

        const matchNome = !busca     || nome.includes(busca);
        const matchCat  = !categoria || cat === categoria;
        const matchSts  = filtroStatus === "todos"
            || (filtroStatus === "ativas"   && status === "ativa")
            || (filtroStatus === "quitadas" && status === "quitada");

        const visivel = matchNome && matchCat && matchSts;
        card.classList.toggle("hidden", !visivel);
        if (visivel) visiveis++;
    });
}

filtrosBusca?.addEventListener("input", aplicarFiltros);
filtrosCategoria?.addEventListener("change", aplicarFiltros);

filtroPills.forEach((pill) => {
    pill.addEventListener("click", () => {
        filtroPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        filtroStatus = pill.dataset.filtro;
        aplicarFiltros();
    });
});

// ---------------------------------------------------------------------------
// Exportar CSV
// ---------------------------------------------------------------------------
$("btn-exportar-csv")?.addEventListener("click", () => {
    const cards = document.querySelectorAll(".divida-card");
    if (!cards.length) { showToast("Nenhuma dívida para exportar.", "error"); return; }

    const linhas = [["ID", "Nome", "Categoria", "Valor Total", "Parcela", "Parcelas Pagas", "Total Parcelas", "Valor Restante", "Status"]];

    cards.forEach((card) => {
        const id      = card.dataset.id ?? "";
        const nome    = card.dataset.cat !== undefined ? card.querySelector(".divida-nome")?.textContent?.trim() ?? "" : "";
        const cat     = card.dataset.cat ?? "";
        const status  = card.dataset.status === "quitada" ? "Quitada" : "Ativa";
        const valores = card.querySelectorAll(".valor-num");
        const restante = valores[0]?.textContent?.replace("R$ ", "").replace(/\./g, "").replace(",", ".") ?? "";
        const total    = valores[1]?.textContent?.replace("R$ ", "").replace(/\./g, "").replace(",", ".") ?? "";
        const parcela  = valores[2]?.textContent?.replace("R$ ", "").replace(/\./g, "").replace(",", ".") ?? "";
        const labels   = card.querySelector(".progress-labels")?.textContent?.trim() ?? "";
        const matchParcelas = labels.match(/(\d+)\/(\d+)/);
        const pagas = matchParcelas?.[1] ?? "";
        const totalParc = matchParcelas?.[2] ?? "";

        linhas.push([id, nome, cat, total, parcela, pagas, totalParc, restante, status]);
    });

    const csv     = linhas.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob    = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url     = URL.createObjectURL(blob);
    const link    = document.createElement("a");
    link.href     = url;
    link.download = `dividas_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("CSV exportado!", "success");
});

// ---------------------------------------------------------------------------
// Simulador de Pagamento Antecipado
// ---------------------------------------------------------------------------
$("btn-abrir-simulador")?.addEventListener("click", () => {
    modalSimulador?.classList.add("is-active");
    document.body.style.overflow = "hidden";
    $("sim-result")?.classList.remove("visible");
});

$("btn-simular")?.addEventListener("click", () => {
    const select    = $("sim-divida");
    const opt       = select?.options[select.selectedIndex];
    const extra     = parseFloat($("sim-extra")?.value);

    if (!opt || !extra || extra <= 0) {
        showToast("Informe o valor extra mensal.", "error");
        return;
    }

    const restante  = parseFloat(opt.dataset.restante);
    const parcela   = parseFloat(opt.dataset.parcela);
    const parcelasOrig = parseInt(opt.dataset.restantes, 10);

    const novaParcela   = parcela + extra;
    const parcelasNovo  = Math.ceil(restante / novaParcela);
    const economia      = Math.max(0, parcelasOrig - parcelasNovo);

    $("sim-parcelas-orig").textContent = `${parcelasOrig} meses`;
    $("sim-parcelas-novo").textContent = `${parcelasNovo} meses`;
    $("sim-economia-meses").textContent = economia > 0
        ? `${economia} meses a menos! 🎉`
        : "Nenhuma economia";

    $("sim-result")?.classList.add("visible");
});

// ---------------------------------------------------------------------------
// Gráfico de Rosca (Chart.js)
// ---------------------------------------------------------------------------
const donutDataEl = $("donut-data");
if (donutDataEl && typeof Chart !== "undefined") {
    const raw    = JSON.parse(donutDataEl.textContent);
    const labels = raw.map((d) => d.label);
    const values = raw.map((d) => d.value);
    const colors = labels.map((l) => CAT_COLORS[l] ?? "#8E8E93");

    const ctx = $("donut-chart")?.getContext("2d");
    if (ctx) {
        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 6,
                }],
            },
            options: {
                cutout: "68%",
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` R$ ${ctx.parsed.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`,
                        },
                    },
                },
                animation: { animateRotate: true, duration: 800 },
            },
        });

        // Legenda personalizada
        const legend = $("chart-legend");
        if (legend) {
            legend.innerHTML = "";
            labels.forEach((label, i) => {
                const item = document.createElement("div");
                item.className = "legend-item";
                item.innerHTML = `
                    <span class="legend-dot" style="background:${colors[i]}"></span>
                    <span class="legend-label">${label}</span>
                    <span class="legend-value">R$ ${values[i].toLocaleString("pt-BR", { minimumFractionDigits: 0 })}</span>
                `;
                legend.appendChild(item);
            });
        }
    }
}

// ---------------------------------------------------------------------------
// Navbar: scroll para glassmorphism mais pronunciado
// ---------------------------------------------------------------------------
window.addEventListener("scroll", () => {
    const navbar = $("navbar");
    if (!navbar) return;
    const isDark = HTML.getAttribute("data-theme") === "dark";
    if (window.scrollY > 10) {
        navbar.style.background = isDark ? "rgba(28,28,30,0.96)" : "rgba(255,255,255,0.96)";
    } else {
        navbar.style.background = isDark ? "rgba(28,28,30,0.85)" : "rgba(255,255,255,0.82)";
    }
}, { passive: true });
