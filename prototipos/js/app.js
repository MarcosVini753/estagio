const STORAGE_KEY = 'bibliotecaUfacPrototypeState.v1';

const defaultState = {
  role: 'usuario',
  userScreen: 'computadores',
  supervisorScreen: 'configuracao',
  selectedDay: 'today',
  search: '',
  activeSession: null,
  bookings: [
    { id: 1, computerId: 4, dateKey: 'tomorrow', slot: '09:00 - 10:00', status: 'confirmado' }
  ],
  incidents: [],
  turnos: [
    { nome: '1º Turno', inicio: '07:15', fim: '13:00' },
    { nome: '2º Turno', inicio: '13:00', fim: '17:00' },
    { nome: '3º Turno', inicio: '17:00', fim: '21:00' }
  ],
  reportParams: {
    mesReferencia: 'Dezembro/2025',
    formatoPadrao: 'PDF',
    agruparPor: 'Turno'
  },
  computers: [
    { id: 1, number: '01', room: 'Sala Virtual', statusToday: 'available', statusTomorrow: 'available', notes: 'Próximo à entrada' },
    { id: 2, number: '02', room: 'Sala Virtual', statusToday: 'busy', statusTomorrow: 'available', notes: 'Uso corrente' },
    { id: 3, number: '03', room: 'Sala Virtual', statusToday: 'available', statusTomorrow: 'reserved', notes: 'Monitor maior' },
    { id: 4, number: '04', room: 'Sala Virtual', statusToday: 'blocked', statusTomorrow: 'available', notes: 'Aguardando liberação' },
    { id: 5, number: '05', room: 'Sala Virtual', statusToday: 'available', statusTomorrow: 'available', notes: 'Cabine individual' },
    { id: 6, number: '06', room: 'Sala Virtual', statusToday: 'reserved', statusTomorrow: 'available', notes: 'Reserva no fim da tarde' },
    { id: 7, number: '07', room: 'Sala Virtual', statusToday: 'available', statusTomorrow: 'available', notes: 'Boa acessibilidade' },
    { id: 8, number: '08', room: 'Sala Virtual', statusToday: 'busy', statusTomorrow: 'available', notes: 'Em uso' }
  ],
  usageRecords: [
    { day: 1, turno: '1º Turno', curso: 'Sistemas de Informação', computer: '01', total: 7 },
    { day: 1, turno: '2º Turno', curso: 'Direito', computer: '02', total: 11 },
    { day: 2, turno: '1º Turno', curso: 'Pedagogia', computer: '05', total: 5 },
    { day: 2, turno: '2º Turno', curso: 'Administração', computer: '03', total: 10 },
    { day: 3, turno: '1º Turno', curso: 'Sistemas de Informação', computer: '07', total: 9 },
    { day: 3, turno: '2º Turno', curso: 'Letras', computer: '01', total: 15 },
    { day: 4, turno: '2º Turno', curso: 'Matemática', computer: '04', total: 12 },
    { day: 5, turno: '1º Turno', curso: 'Enfermagem', computer: '06', total: 8 },
    { day: 5, turno: '2º Turno', curso: 'Sistemas de Informação', computer: '08', total: 11 }
  ]
};

const app = document.getElementById('appContent');
const bottomNav = document.getElementById('bottomNav');
const screenTitle = document.getElementById('screenTitle');
const searchInput = document.getElementById('searchInput');
const modalRoot = document.getElementById('modalRoot');
const modalTitle = document.getElementById('modalTitle');
const modalBody = document.getElementById('modalBody');
const toast = document.getElementById('toast');

let state = loadState();
let selectedSlot = null;
let touchStartX = 0;

function loadState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : structuredClone(defaultState);
  } catch (error) {
    return structuredClone(defaultState);
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function resetState() {
  state = structuredClone(defaultState);
  saveState();
  render();
  showToast('Dados simulados reiniciados.');
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  window.setTimeout(() => toast.classList.remove('show'), 2200);
}

function normalize(text) {
  return String(text || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function todayLabel(dayKey = state.selectedDay) {
  if (dayKey === 'today') return 'Dia atual';
  return 'Próximo dia';
}

function computerStatus(computer, dayKey = state.selectedDay) {
  if (state.activeSession?.computerId === computer.id && dayKey === 'today') return 'mine';
  return dayKey === 'today' ? computer.statusToday : computer.statusTomorrow;
}

function statusMeta(status) {
  const map = {
    available: { label: 'Disponível', badge: 'ok', avatar: '', description: 'Pronto para uso' },
    busy: { label: 'Ocupado', badge: 'busy', avatar: 'busy', description: 'Em sessão de uso' },
    blocked: { label: 'Indisp.', badge: 'danger', avatar: 'blocked', description: 'Indisponível ou em manutenção' },
    reserved: { label: 'Reservado', badge: 'warn', avatar: 'reserved', description: 'Possui reserva no período' },
    mine: { label: 'Em uso', badge: 'info', avatar: '', description: 'Sua sessão ativa' }
  };
  return map[status] || map.available;
}

function filteredComputers() {
  const q = normalize(state.search);
  return state.computers.filter((computer) => {
    const status = statusMeta(computerStatus(computer));
    const haystack = normalize(`${computer.number} ${computer.room} ${computer.notes} ${status.label}`);
    return !q || haystack.includes(q);
  });
}

function render() {
  document.querySelectorAll('.role-option').forEach((button) => {
    button.classList.toggle('active', button.dataset.role === state.role);
  });
  searchInput.value = state.search;
  if (state.role === 'usuario') renderUser();
  if (state.role === 'supervisor') renderSupervisor();
}

function setBottomNav(items, activeKey, handler) {
  bottomNav.style.gridTemplateColumns = `repeat(${items.length}, 1fr)`;
  bottomNav.innerHTML = items.map((item) => `
    <button class="nav-item ${item.key === activeKey ? 'active' : ''}" data-nav-key="${item.key}">
      <span>${item.icon}</span>
      <span>${item.label}</span>
    </button>
  `).join('');

  bottomNav.querySelectorAll('[data-nav-key]').forEach((button) => {
    button.addEventListener('click', () => handler(button.dataset.navKey));
  });
}

function renderUser() {
  screenTitle.textContent = 'Sala de Informática';
  setBottomNav([
    { key: 'computadores', label: 'Computadores', icon: '▦' },
    { key: 'agendamentos', label: 'Agenda', icon: '□' },
    { key: 'sessao', label: 'Sessão', icon: '◉' },
    { key: 'problemas', label: 'Problemas', icon: '!' }
  ], state.userScreen, (key) => {
    state.userScreen = key;
    saveState();
    render();
  });

  if (state.userScreen === 'computadores') renderUserComputers();
  if (state.userScreen === 'agendamentos') renderUserBookings();
  if (state.userScreen === 'sessao') renderUserSession();
  if (state.userScreen === 'problemas') renderUserIncidents();
}

function renderUserComputers() {
  const computers = filteredComputers();
  app.innerHTML = `
    ${state.activeSession ? activeSessionCard() : ''}
    <div class="day-tabs" aria-label="Alternar dia">
      <button class="day-tab ${state.selectedDay === 'today' ? 'active' : ''}" data-day="today">Hoje</button>
      <button class="day-tab ${state.selectedDay === 'tomorrow' ? 'active' : ''}" data-day="tomorrow">Amanhã</button>
    </div>
    <p class="section-title">${todayLabel()} — computadores</p>
    <section class="list" id="computerList">
      ${computers.map(renderComputerItem).join('') || emptyState('Nenhum computador encontrado para a busca atual.')}
    </section>
    <p class="helper-text">Deslize a lista para a esquerda ou direita para alternar entre o dia atual e o próximo dia.</p>
  `;

  app.querySelectorAll('[data-day]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedDay = button.dataset.day;
      saveState();
      renderUserComputers();
    });
  });

  app.querySelectorAll('[data-computer-id]').forEach((button) => {
    button.addEventListener('click', () => openComputerModal(Number(button.dataset.computerId)));
  });

  const list = document.getElementById('computerList');
  list.addEventListener('touchstart', (event) => {
    touchStartX = event.changedTouches[0].screenX;
  }, { passive: true });

  list.addEventListener('touchend', (event) => {
    const delta = event.changedTouches[0].screenX - touchStartX;
    if (Math.abs(delta) < 60) return;
    state.selectedDay = delta < 0 ? 'tomorrow' : 'today';
    saveState();
    renderUserComputers();
  }, { passive: true });
}

function renderComputerItem(computer) {
  const status = computerStatus(computer);
  const meta = statusMeta(status);
  const tomorrowSlots = availableSlots(computer.id, 'tomorrow').length;
  const subtitle = state.selectedDay === 'tomorrow'
    ? `${tomorrowSlots} horários disponíveis para agendamento`
    : `${meta.description} · ${computer.notes}`;

  return `
    <button class="list-item" data-computer-id="${computer.id}">
      <span class="avatar ${meta.avatar}">PC${computer.number}</span>
      <span class="item-main">
        <span class="item-title">Computador ${computer.number}</span>
        <span class="item-description">${escapeHtml(subtitle)}</span>
      </span>
      <span class="item-side">
        <span class="small-time">${state.selectedDay === 'today' ? 'Hoje' : 'Amanhã'}</span>
        <span class="badge ${meta.badge}">${meta.label}</span>
      </span>
    </button>
  `;
}

function activeSessionCard() {
  const computer = state.computers.find((item) => item.id === state.activeSession.computerId);
  return `
    <section class="summary-card">
      <div class="summary-row">
        <div>
          <p class="summary-title">Sessão ativa</p>
          <p class="summary-subtitle">Computador ${computer?.number || '--'} · Entrada registrada às ${state.activeSession.startTime}</p>
        </div>
        <span class="badge info">Ativa</span>
      </div>
      <div class="quick-actions">
        <button class="btn primary" onclick="registerExit()">Registrar saída</button>
        <button class="btn" onclick="state.userScreen='computadores'; saveState(); render();">Trocar computador</button>
      </div>
    </section>
  `;
}

function renderUserBookings() {
  const userBookings = state.bookings.filter((booking) => booking.status === 'confirmado');
  app.innerHTML = `
    <section class="summary-card">
      <div class="summary-row">
        <div>
          <p class="summary-title">Meus agendamentos</p>
          <p class="summary-subtitle">O protótipo restringe novos agendamentos ao próximo dia.</p>
        </div>
        <span class="badge ok">${userBookings.length}</span>
      </div>
      <button class="btn primary full" onclick="state.userScreen='computadores'; state.selectedDay='tomorrow'; saveState(); render();">Agendar computador para amanhã</button>
    </section>
    <p class="section-title">Reservas confirmadas</p>
    <section class="list">
      ${userBookings.map((booking) => {
        const computer = state.computers.find((item) => item.id === booking.computerId);
        return `
          <button class="list-item" data-booking-id="${booking.id}">
            <span class="avatar reserved">PC${computer?.number || '--'}</span>
            <span class="item-main">
              <span class="item-title">Computador ${computer?.number || '--'}</span>
              <span class="item-description">${todayLabel(booking.dateKey)} · ${booking.slot}</span>
            </span>
            <span class="item-side">
              <span class="small-time">Reserva</span>
              <span class="badge warn">Confirmado</span>
            </span>
          </button>
        `;
      }).join('') || emptyState('Nenhum agendamento confirmado.')}
    </section>
  `;

  app.querySelectorAll('[data-booking-id]').forEach((button) => {
    button.addEventListener('click', () => openBookingModal(Number(button.dataset.bookingId)));
  });
}

function renderUserSession() {
  if (!state.activeSession) {
    app.innerHTML = `
      <section class="empty-state">
        <h2>Nenhuma sessão ativa</h2>
        <p class="helper-text">Para iniciar o uso da sala, acesse a lista de computadores do dia atual e escolha uma máquina disponível.</p>
        <button class="btn primary full" onclick="state.userScreen='computadores'; state.selectedDay='today'; saveState(); render();">Ver computadores de hoje</button>
      </section>
    `;
    return;
  }

  const computer = state.computers.find((item) => item.id === state.activeSession.computerId);
  app.innerHTML = `
    <section class="summary-card">
      <p class="summary-title">Sessão atual</p>
      <p class="summary-subtitle">Computador ${computer?.number || '--'} · início às ${state.activeSession.startTime}</p>
      <div class="metric-grid">
        <div class="metric-card">
          <p class="helper-text">Status</p>
          <p class="metric-value">Ativa</p>
        </div>
        <div class="metric-card">
          <p class="helper-text">Trocas</p>
          <p class="metric-value">${state.activeSession.exchanges.length}</p>
        </div>
      </div>
      <div class="quick-actions">
        <button class="btn primary" onclick="registerExit()">Registrar saída</button>
        <button class="btn" onclick="state.userScreen='computadores'; state.selectedDay='today'; saveState(); render();">Trocar computador</button>
        <button class="btn warning" onclick="openIncidentModal(${computer?.id || 0})">Informar problema</button>
      </div>
    </section>
    <p class="section-title">Histórico de troca</p>
    <section class="list">
      ${state.activeSession.exchanges.map((exchange, index) => `
        <div class="list-item">
          <span class="avatar">${index + 1}</span>
          <span class="item-main">
            <span class="item-title">Troca registrada</span>
            <span class="item-description">PC${exchange.from} → PC${exchange.to}</span>
          </span>
          <span class="item-side"><span class="small-time">${exchange.time}</span></span>
        </div>
      `).join('') || emptyState('Nenhuma troca realizada nesta sessão.')}
    </section>
  `;
}

function renderUserIncidents() {
  app.innerHTML = `
    <section class="summary-card">
      <p class="summary-title">Comunicação de problemas</p>
      <p class="summary-subtitle">Registre falhas percebidas durante o uso ou escolha um computador na lista para associar o problema diretamente a ele.</p>
      <button class="btn primary full" onclick="openIncidentModal()">Informar problema no computador</button>
    </section>
    <p class="section-title">Ocorrências enviadas neste protótipo</p>
    <section class="list">
      ${state.incidents.map((incident) => `
        <div class="list-item">
          <span class="avatar blocked">!</span>
          <span class="item-main">
            <span class="item-title">Computador ${incident.computerNumber}</span>
            <span class="item-description">${escapeHtml(incident.description)}</span>
          </span>
          <span class="item-side"><span class="small-time">${incident.time}</span><span class="badge warn">Aberta</span></span>
        </div>
      `).join('') || emptyState('Nenhuma ocorrência registrada.')}
    </section>
  `;
}

function openComputerModal(computerId) {
  const computer = state.computers.find((item) => item.id === computerId);
  if (!computer) return;
  const status = computerStatus(computer);
  const meta = statusMeta(status);
  selectedSlot = null;

  if (state.selectedDay === 'tomorrow') {
    openScheduleModal(computer);
    return;
  }

  const canEnter = status === 'available' && !state.activeSession;
  const canExchange = status === 'available' && state.activeSession && state.activeSession.computerId !== computer.id;
  const isMine = state.activeSession?.computerId === computer.id;

  openModal(`Computador ${computer.number}`, `
    <section class="summary-card">
      <p class="summary-title">Status: ${meta.label}</p>
      <p class="summary-subtitle">${escapeHtml(computer.notes)} · ${computer.room}</p>
    </section>
    <div class="form-grid">
      ${canEnter ? `<button class="btn primary full" onclick="registerEntry(${computer.id})">Registrar entrada</button>` : ''}
      ${canExchange ? `<button class="btn primary full" onclick="exchangeComputer(${computer.id})">Trocar para este computador</button>` : ''}
      ${isMine ? `<button class="btn primary full" onclick="registerExit()">Registrar saída</button>` : ''}
      <button class="btn full" onclick="openScheduleModalById(${computer.id})">Consultar horários disponíveis</button>
      <button class="btn warning full" onclick="openIncidentModal(${computer.id})">Informar problema no computador</button>
      ${!canEnter && !canExchange && !isMine ? `<p class="helper-text">Este computador não está disponível para entrada ou troca no momento.</p>` : ''}
    </div>
  `);
}

function openScheduleModalById(computerId) {
  const computer = state.computers.find((item) => item.id === computerId);
  if (computer) openScheduleModal(computer);
}

function openScheduleModal(computer) {
  const slots = slotsForDay('tomorrow');
  const available = availableSlots(computer.id, 'tomorrow');
  const booked = state.bookings.filter((booking) => booking.computerId === computer.id && booking.dateKey === 'tomorrow' && booking.status === 'confirmado').map((booking) => booking.slot);
  openModal(`Agendar PC${computer.number}`, `
    <section class="summary-card">
      <p class="summary-title">Agendamento para o próximo dia</p>
      <p class="summary-subtitle">Selecione um horário livre e confirme o agendamento.</p>
    </section>
    <div class="slot-grid">
      ${slots.map((slot) => `
        <button class="slot-btn" data-slot="${slot}" ${booked.includes(slot) ? 'disabled' : ''}>${slot}</button>
      `).join('')}
    </div>
    <br />
    <button class="btn primary full" id="confirmScheduleBtn" disabled>Confirmar agendamento</button>
    <p class="helper-text">Horários ocupados ficam desabilitados. Agendamento para datas posteriores ao próximo dia não é permitido nesta versão.</p>
  `);

  modalBody.querySelectorAll('[data-slot]').forEach((button) => {
    button.addEventListener('click', () => {
      selectedSlot = button.dataset.slot;
      modalBody.querySelectorAll('[data-slot]').forEach((item) => item.classList.remove('selected'));
      button.classList.add('selected');
      document.getElementById('confirmScheduleBtn').disabled = false;
    });
  });

  document.getElementById('confirmScheduleBtn').addEventListener('click', () => {
    if (!selectedSlot || !available.includes(selectedSlot)) return;
    state.bookings.push({
      id: Date.now(),
      computerId: computer.id,
      dateKey: 'tomorrow',
      slot: selectedSlot,
      status: 'confirmado'
    });
    saveState();
    closeModal();
    state.userScreen = 'agendamentos';
    showToast('Agendamento confirmado.');
    render();
  });
}

function openBookingModal(bookingId) {
  const booking = state.bookings.find((item) => item.id === bookingId);
  if (!booking) return;
  const computer = state.computers.find((item) => item.id === booking.computerId);
  openModal('Agendamento confirmado', `
    <section class="summary-card">
      <p class="summary-title">Computador ${computer?.number || '--'}</p>
      <p class="summary-subtitle">${todayLabel(booking.dateKey)} · ${booking.slot}</p>
    </section>
    <button class="btn danger full" onclick="cancelBooking(${booking.id})">Cancelar agendamento</button>
  `);
}

function cancelBooking(bookingId) {
  state.bookings = state.bookings.map((booking) => booking.id === bookingId ? { ...booking, status: 'cancelado' } : booking);
  saveState();
  closeModal();
  render();
  showToast('Agendamento cancelado.');
}

function registerEntry(computerId) {
  if (state.activeSession) {
    showToast('Já existe uma sessão ativa.');
    return;
  }
  const computer = state.computers.find((item) => item.id === computerId);
  if (!computer || computerStatus(computer, 'today') !== 'available') {
    showToast('Computador indisponível para entrada.');
    return;
  }
  state.activeSession = {
    id: Date.now(),
    computerId,
    computerNumber: computer.number,
    startTime: nowTime(),
    exchanges: []
  };
  computer.statusToday = 'busy';
  saveState();
  closeModal();
  state.userScreen = 'sessao';
  render();
  showToast('Entrada registrada.');
}

function exchangeComputer(newComputerId) {
  if (!state.activeSession) {
    showToast('Não há sessão ativa para troca.');
    return;
  }
  const current = state.computers.find((item) => item.id === state.activeSession.computerId);
  const target = state.computers.find((item) => item.id === newComputerId);
  if (!target || target.statusToday !== 'available') {
    showToast('Computador de destino indisponível.');
    return;
  }
  if (current) current.statusToday = 'available';
  target.statusToday = 'busy';
  state.activeSession.exchanges.push({
    from: current?.number || '--',
    to: target.number,
    time: nowTime()
  });
  state.activeSession.computerId = target.id;
  state.activeSession.computerNumber = target.number;
  saveState();
  closeModal();
  state.userScreen = 'sessao';
  render();
  showToast('Troca de computador registrada.');
}

function registerExit() {
  if (!state.activeSession) {
    showToast('Não há sessão ativa.');
    return;
  }
  const computer = state.computers.find((item) => item.id === state.activeSession.computerId);
  if (computer) computer.statusToday = 'available';
  state.usageRecords.push({
    day: new Date().getDate(),
    turno: inferTurno(nowTime()),
    curso: 'Sistemas de Informação',
    computer: computer?.number || '--',
    total: 1
  });
  state.activeSession = null;
  saveState();
  closeModal();
  state.userScreen = 'computadores';
  render();
  showToast('Saída registrada e computador liberado.');
}

function openIncidentModal(computerId = null) {
  const options = state.computers.map((computer) => `<option value="${computer.id}" ${computer.id === computerId ? 'selected' : ''}>Computador ${computer.number}</option>`).join('');
  openModal('Informar problema', `
    <form id="incidentForm" class="form-grid">
      <div class="field">
        <label for="incidentComputer">Computador</label>
        <select id="incidentComputer" required>${options}</select>
      </div>
      <div class="field">
        <label for="incidentDescription">Descrição do problema</label>
        <textarea id="incidentDescription" placeholder="Ex.: mouse não funciona, computador travando, tela apagando..." required></textarea>
      </div>
      <button class="btn primary full" type="submit">Enviar ocorrência</button>
    </form>
  `);

  document.getElementById('incidentForm').addEventListener('submit', (event) => {
    event.preventDefault();
    const selectedComputer = state.computers.find((item) => item.id === Number(document.getElementById('incidentComputer').value));
    const description = document.getElementById('incidentDescription').value.trim();
    if (!selectedComputer || !description) return;
    state.incidents.unshift({
      id: Date.now(),
      computerId: selectedComputer.id,
      computerNumber: selectedComputer.number,
      description,
      time: nowTime(),
      status: 'Aberta'
    });
    saveState();
    closeModal();
    state.userScreen = 'problemas';
    render();
    showToast('Ocorrência enviada.');
  });
}

function renderSupervisor() {
  screenTitle.textContent = 'Painel do Supervisor';
  setBottomNav([
    { key: 'configuracao', label: 'Config.', icon: '⚙' },
    { key: 'gerencial', label: 'Gerencial', icon: '▤' },
    { key: 'indicadores', label: 'Indicadores', icon: '◎' },
    { key: 'relatorios', label: 'Relatórios', icon: '▧' }
  ], state.supervisorScreen, (key) => {
    state.supervisorScreen = key;
    saveState();
    render();
  });

  if (state.supervisorScreen === 'configuracao') renderSupervisorConfig();
  if (state.supervisorScreen === 'gerencial') renderSupervisorManagement();
  if (state.supervisorScreen === 'indicadores') renderSupervisorIndicators();
  if (state.supervisorScreen === 'relatorios') renderSupervisorReports();
}

function renderSupervisorConfig() {
  app.innerHTML = `
    <p class="section-title">Configuração do sistema</p>
    <section class="form-card">
      <h2>Cadastrar computadores</h2>
      <form id="computerForm" class="form-grid">
        <div class="field">
          <label for="computerNumber">Número do computador</label>
          <input id="computerNumber" required placeholder="Ex.: 09" />
        </div>
        <div class="field">
          <label for="computerNotes">Observação</label>
          <input id="computerNotes" placeholder="Ex.: Próximo à janela" />
        </div>
        <button class="btn primary full" type="submit">Cadastrar computador</button>
      </form>
    </section>

    <section class="form-card">
      <h2>Configurar turnos</h2>
      <form id="turnosForm" class="form-grid">
        ${state.turnos.map((turno, index) => `
          <div class="field">
            <label>${turno.nome}</label>
            <div class="summary-row">
              <input type="time" value="${turno.inicio}" data-turno-inicio="${index}" />
              <input type="time" value="${turno.fim}" data-turno-fim="${index}" />
            </div>
          </div>
        `).join('')}
        <button class="btn primary full" type="submit">Salvar turnos</button>
      </form>
    </section>

    <section class="form-card">
      <h2>Configurar parâmetros de relatório</h2>
      <form id="reportParamsForm" class="form-grid">
        <div class="field">
          <label for="mesReferencia">Mês de referência</label>
          <input id="mesReferencia" value="${escapeHtml(state.reportParams.mesReferencia)}" />
        </div>
        <div class="field">
          <label for="formatoPadrao">Formato padrão</label>
          <select id="formatoPadrao">
            ${['PDF', 'CSV', 'Planilha'].map((format) => `<option ${format === state.reportParams.formatoPadrao ? 'selected' : ''}>${format}</option>`).join('')}
          </select>
        </div>
        <div class="field">
          <label for="agruparPor">Agrupar por</label>
          <select id="agruparPor">
            ${['Turno', 'Data', 'Computador', 'Curso ou setor'].map((item) => `<option ${item === state.reportParams.agruparPor ? 'selected' : ''}>${item}</option>`).join('')}
          </select>
        </div>
        <button class="btn primary full" type="submit">Salvar parâmetros</button>
      </form>
    </section>

    <p class="section-title">Computadores cadastrados</p>
    <section class="list">
      ${state.computers.map((computer) => `
        <div class="list-item">
          <span class="avatar ${statusMeta(computer.statusToday).avatar}">PC${computer.number}</span>
          <span class="item-main">
            <span class="item-title">Computador ${computer.number}</span>
            <span class="item-description">${escapeHtml(computer.notes)} · ${computer.room}</span>
          </span>
          <span class="item-side">
            <select data-computer-status="${computer.id}" aria-label="Alterar status do computador ${computer.number}">
              ${statusOptions(computer.statusToday)}
            </select>
          </span>
        </div>
      `).join('')}
    </section>
  `;

  document.getElementById('computerForm').addEventListener('submit', (event) => {
    event.preventDefault();
    const number = document.getElementById('computerNumber').value.trim().padStart(2, '0');
    if (!number) return;
    const exists = state.computers.some((computer) => computer.number === number);
    if (exists) {
      showToast('Já existe computador com esse número.');
      return;
    }
    state.computers.push({
      id: Date.now(),
      number,
      room: 'Sala Virtual',
      statusToday: 'available',
      statusTomorrow: 'available',
      notes: document.getElementById('computerNotes').value.trim() || 'Sem observações'
    });
    saveState();
    render();
    showToast('Computador cadastrado.');
  });

  document.getElementById('turnosForm').addEventListener('submit', (event) => {
    event.preventDefault();
    state.turnos = state.turnos.map((turno, index) => ({
      ...turno,
      inicio: document.querySelector(`[data-turno-inicio="${index}"]`).value,
      fim: document.querySelector(`[data-turno-fim="${index}"]`).value
    }));
    saveState();
    showToast('Turnos atualizados.');
  });

  document.getElementById('reportParamsForm').addEventListener('submit', (event) => {
    event.preventDefault();
    state.reportParams = {
      mesReferencia: document.getElementById('mesReferencia').value.trim(),
      formatoPadrao: document.getElementById('formatoPadrao').value,
      agruparPor: document.getElementById('agruparPor').value
    };
    saveState();
    showToast('Parâmetros de relatório salvos.');
  });

  app.querySelectorAll('[data-computer-status]').forEach((select) => {
    select.addEventListener('change', () => {
      const computer = state.computers.find((item) => item.id === Number(select.dataset.computerStatus));
      if (!computer) return;
      computer.statusToday = select.value;
      saveState();
      showToast('Status do computador alterado.');
      render();
    });
  });
}

function statusOptions(current) {
  return [
    ['available', 'Disponível'],
    ['busy', 'Ocupado'],
    ['blocked', 'Indisponível'],
    ['reserved', 'Reservado']
  ].map(([value, label]) => `<option value="${value}" ${current === value ? 'selected' : ''}>${label}</option>`).join('');
}

function renderSupervisorManagement() {
  const periodo = aggregateBy('day');
  const turno = aggregateBy('turno');
  const curso = aggregateBy('curso');
  const computador = aggregateBy('computer');
  app.innerHTML = `
    <p class="section-title">Acompanhamento gerencial</p>
    <section class="summary-card">
      <p class="summary-title">Análise consolidada da sala</p>
      <p class="summary-subtitle">Visualização simulada dos casos: uso por período, turno, curso/setor e computador.</p>
    </section>
    ${renderBarSection('Uso por período', periodo, 'Dia')}
    ${renderBarSection('Uso por turno', turno)}
    ${renderBarSection('Uso por curso ou setor', curso)}
    ${renderBarSection('Uso por computador', computador, 'PC')}
  `;
}

function renderSupervisorIndicators() {
  const total = totalUsage();
  const available = state.computers.filter((computer) => computer.statusToday === 'available').length;
  const busy = state.computers.filter((computer) => computer.statusToday === 'busy').length + (state.activeSession ? 1 : 0);
  const occupation = Math.round((busy / Math.max(state.computers.length, 1)) * 100);
  const days = aggregateBy('day').sort((a, b) => b.value - a.value).slice(0, 3);
  const turns = aggregateBy('turno').sort((a, b) => b.value - a.value);

  app.innerHTML = `
    <p class="section-title">Indicadores da sala</p>
    <section class="metric-grid">
      <div class="metric-card">
        <p class="helper-text">Usos simulados</p>
        <p class="metric-value">${total}</p>
      </div>
      <div class="metric-card">
        <p class="helper-text">Taxa de ocupação</p>
        <p class="metric-value">${occupation}%</p>
      </div>
      <div class="metric-card">
        <p class="helper-text">Disponíveis agora</p>
        <p class="metric-value">${available}</p>
      </div>
      <div class="metric-card">
        <p class="helper-text">Ocorrências abertas</p>
        <p class="metric-value">${state.incidents.length}</p>
      </div>
    </section>

    <br />
    ${renderBarSection('Dias de maior movimento', days, 'Dia')}
    ${renderBarSection('Horários/turnos de maior demanda', turns)}
    <section class="report-card">
      <h2>Acompanhar taxa de ocupação dos computadores</h2>
      <div class="bar-row">
        <span>Ocupação</span>
        <span class="bar-track"><span class="bar-fill" style="width:${occupation}%"></span></span>
        <strong>${occupation}%</strong>
      </div>
      <p class="helper-text">A taxa usa a proporção de computadores ocupados em relação ao total cadastrado no protótipo.</p>
    </section>
  `;
}

function renderSupervisorReports() {
  app.innerHTML = `
    <p class="section-title">Relatórios consolidados</p>
    <section class="summary-card">
      <p class="summary-title">Gerar relatório consolidado</p>
      <p class="summary-subtitle">Selecione o tipo de relatório para gerar uma prévia com totais por turno, período e computador.</p>
      <div class="quick-actions">
        <button class="btn primary" data-report="diário">Diário</button>
        <button class="btn primary" data-report="semanal">Semanal</button>
        <button class="btn primary" data-report="mensal">Mensal</button>
        <button class="btn primary" data-report="anual">Anual</button>
      </div>
    </section>
    <section id="reportResult" class="report-card">
      <h2>Prévia do relatório</h2>
      <p class="helper-text">Nenhum relatório gerado nesta sessão.</p>
    </section>
  `;

  app.querySelectorAll('[data-report]').forEach((button) => {
    button.addEventListener('click', () => {
      const type = button.dataset.report;
      document.getElementById('reportResult').innerHTML = `
        <h2>Relatório ${type} consolidado</h2>
        <pre class="report-preview">${escapeHtml(generateReport(type))}</pre>
      `;
      showToast(`Relatório ${type} gerado.`);
    });
  });
}

function generateReport(type) {
  const byTurn = aggregateBy('turno');
  const byComputer = aggregateBy('computer');
  const lines = [];
  lines.push('UNIVERSIDADE FEDERAL DO ACRE');
  lines.push('Biblioteca Central - Sala de Informática');
  lines.push(`Tipo: Relatório ${type} consolidado`);
  lines.push(`Referência: ${state.reportParams.mesReferencia}`);
  lines.push(`Agrupamento padrão: ${state.reportParams.agruparPor}`);
  lines.push('');
  lines.push(`Total geral de usos: ${totalUsage()}`);
  lines.push(`Computadores cadastrados: ${state.computers.length}`);
  lines.push(`Ocorrências abertas: ${state.incidents.length}`);
  lines.push('');
  lines.push('Totais por turno:');
  byTurn.forEach((item) => lines.push(`- ${item.label}: ${item.value}`));
  lines.push('');
  lines.push('Totais por computador:');
  byComputer.forEach((item) => lines.push(`- PC${item.label}: ${item.value}`));
  return lines.join('\n');
}

function renderBarSection(title, data, prefix = '') {
  const max = Math.max(...data.map((item) => item.value), 1);
  return `
    <section class="report-card">
      <h2>${title}</h2>
      ${data.map((item) => `
        <div class="bar-row">
          <span>${prefix ? `${prefix} ` : ''}${escapeHtml(item.label)}</span>
          <span class="bar-track"><span class="bar-fill" style="width:${Math.round((item.value / max) * 100)}%"></span></span>
          <strong>${item.value}</strong>
        </div>
      `).join('')}
    </section>
  `;
}

function aggregateBy(field) {
  const map = new Map();
  state.usageRecords.forEach((record) => {
    const key = record[field];
    map.set(key, (map.get(key) || 0) + record.total);
  });
  return Array.from(map.entries()).map(([label, value]) => ({ label, value }));
}

function totalUsage() {
  return state.usageRecords.reduce((sum, record) => sum + record.total, 0);
}

function availableSlots(computerId, dayKey) {
  const booked = state.bookings
    .filter((booking) => booking.computerId === computerId && booking.dateKey === dayKey && booking.status === 'confirmado')
    .map((booking) => booking.slot);
  return slotsForDay(dayKey).filter((slot) => !booked.includes(slot));
}

function slotsForDay(dayKey) {
  if (dayKey === 'today') return ['08:00 - 09:00', '09:00 - 10:00', '10:00 - 11:00', '14:00 - 15:00', '15:00 - 16:00'];
  return ['07:30 - 08:30', '08:30 - 09:30', '09:30 - 10:30', '10:30 - 11:30', '13:00 - 14:00', '14:00 - 15:00', '15:00 - 16:00', '16:00 - 17:00'];
}

function inferTurno(time) {
  const value = timeToMinutes(time);
  const turno = state.turnos.find((item) => value >= timeToMinutes(item.inicio) && value <= timeToMinutes(item.fim));
  return turno?.nome || 'Fora do turno';
}

function timeToMinutes(time) {
  const [hour, minute] = time.split(':').map(Number);
  return hour * 60 + minute;
}

function nowTime() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function emptyState(message) {
  return `<section class="empty-state"><p class="helper-text">${escapeHtml(message)}</p></section>`;
}

function openModal(title, html) {
  modalTitle.textContent = title;
  modalBody.innerHTML = html;
  modalRoot.classList.remove('hidden');
  modalRoot.setAttribute('aria-hidden', 'false');
}

function closeModal() {
  modalRoot.classList.add('hidden');
  modalRoot.setAttribute('aria-hidden', 'true');
  selectedSlot = null;
}

window.cancelBooking = cancelBooking;
window.registerEntry = registerEntry;
window.registerExit = registerExit;
window.exchangeComputer = exchangeComputer;
window.openIncidentModal = openIncidentModal;
window.openScheduleModalById = openScheduleModalById;
window.state = state;
window.saveState = saveState;
window.render = render;

searchInput.addEventListener('input', (event) => {
  state.search = event.target.value;
  saveState();
  render();
});

document.querySelectorAll('.role-option').forEach((button) => {
  button.addEventListener('click', () => {
    state.role = button.dataset.role;
    state.search = '';
    saveState();
    render();
  });
});

document.getElementById('resetStateBtn').addEventListener('click', resetState);

document.querySelectorAll('[data-close-modal]').forEach((button) => {
  button.addEventListener('click', closeModal);
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeModal();
});

render();
