/* ============================================================
   국내외 규격 및 가이던스 업데이트 검토대장 — 프론트엔드 로직
   데이터 소스: ./data/register.json, ./data/gap/{gap_id}.json
   (실제 데이터는 GitHub Actions 크롤러가 매월 이 파일들을 갱신합니다)
   ============================================================ */

const state = {
  items: [],
  filtered: [],
  selectedId: null,
  months: [],       // ["2026-01", "2026-02", ...]
  selectedMonthIdx: 0 // 0 = 전체
};

const $ = (sel) => document.querySelector(sel);

async function init() {
  try {
    const res = await fetch('data/register.json', { cache: 'no-store' });
    const json = await res.json();
    state.items = json.items || [];
    $('#lastUpdated').textContent = '최종 갱신: ' + (json.meta?.generated_at?.slice(0, 16).replace('T', ' ') || '-');
    $('#sourceCount').textContent = `수집 항목 ${state.items.length}건 · 8개 기관 모니터링`;
  } catch (e) {
    console.error('데이터 로드 실패', e);
    $('#registerBody').innerHTML = `<tr><td colspan="8" class="empty-state">검토대장 데이터를 불러오지 못했습니다. data/register.json 파일을 확인하세요.</td></tr>`;
    return;
  }

  buildMonthRange();
  buildFilterOptions();
  bindEvents();
  applyFilters();
}

/* ---------------- 월 슬라이더 범위 계산 (2026-01 ~ 현재월) ---------------- */
function buildMonthRange() {
  const start = { y: 2026, m: 1 };
  const now = new Date();
  const end = { y: now.getFullYear(), m: now.getMonth() + 1 };

  const months = [];
  let y = start.y, m = start.m;
  while (y < end.y || (y === end.y && m <= end.m)) {
    months.push(`${y}-${String(m).padStart(2, '0')}`);
    m++;
    if (m > 12) { m = 1; y++; }
  }
  state.months = months;

  const slider = $('#monthSlider');
  slider.max = months.length; // 0 = 전체, 1..N = 각 월
  slider.value = 0;
}

function monthLabel(idx) {
  if (idx === 0) return '전체 기간';
  const ym = state.months[idx - 1];
  const [y, m] = ym.split('-');
  return `${y}년 ${parseInt(m, 10)}월`;
}

/* ---------------- 필터 옵션 (기관 / 적용범위) ---------------- */
function buildFilterOptions() {
  const agencies = [...new Set(state.items.map(i => i.agency_kr).filter(Boolean))];
  const scopes = [...new Set(state.items.map(i => i.scope).filter(Boolean))];

  const agencySel = $('#agencyFilter');
  agencies.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a; opt.textContent = a;
    agencySel.appendChild(opt);
  });

  const scopeSel = $('#scopeFilter');
  scopes.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    scopeSel.appendChild(opt);
  });
}

/* ---------------- 이벤트 바인딩 ---------------- */
function bindEvents() {
  $('#monthSlider').addEventListener('input', (e) => {
    state.selectedMonthIdx = parseInt(e.target.value, 10);
    $('#monthSliderLabel').textContent = monthLabel(state.selectedMonthIdx);
    applyFilters();
  });
  $('#agencyFilter').addEventListener('change', applyFilters);
  $('#scopeFilter').addEventListener('change', applyFilters);
  $('#sopOnly').addEventListener('change', applyFilters);
  $('#downloadXlsx').addEventListener('click', downloadXlsx);
}

/* ---------------- 필터 적용 + 테이블 렌더 ---------------- */
function applyFilters() {
  const agency = $('#agencyFilter').value;
  const scope = $('#scopeFilter').value;
  const sopOnly = $('#sopOnly').checked;
  const monthIdx = state.selectedMonthIdx;

  state.filtered = state.items.filter(item => {
    if (agency && item.agency_kr !== agency) return false;
    if (scope && item.scope !== scope) return false;
    if (sopOnly && !item.sop_flag) return false;
    if (monthIdx > 0) {
      const ym = state.months[monthIdx - 1];
      const matchPub = item.published_date && item.published_date.startsWith(ym);
      const matchEff = item.effective_date && item.effective_date.startsWith(ym);
      if (!matchPub && !matchEff) return false;
    }
    return true;
  });

  renderTable();
}

/* ---------------- 검토대장 테이블 렌더 ---------------- */
function renderTable() {
  const tbody = $('#registerBody');
  tbody.innerHTML = '';

  if (state.filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-state">선택한 조건에 해당하는 항목이 없습니다.</td></tr>`;
    return;
  }

  state.filtered.forEach((item, idx) => {
    const tr = document.createElement('tr');
    tr.dataset.id = item.id;
    if (!item.verified) tr.classList.add('unverified');
    if (item.id === state.selectedId) tr.classList.add('selected');

    const linkUrl = item.source_type === 'direct' ? item.source_url : item.fallback_url;
    const linkBadge = item.source_type === 'direct'
      ? '<span class="badge badge-direct">직접링크</span>'
      : (item.source_type === 'unverified'
          ? '<span class="badge badge-unverified">미확인</span>'
          : '<span class="badge badge-fallback">목록링크</span>');

    tr.innerHTML = `
      <td class="col-no">${idx + 1}</td>
      <td class="col-date">${item.published_date || '-'}</td>
      <td class="col-date">${item.effective_date || '-'}</td>
      <td class="col-pub">${item.agency_kr || item.publisher || '-'}</td>
      <td class="col-regno"><span class="reg-no-mono">${item.reg_no || '-'}</span></td>
      <td class="col-title">
        <a class="reg-title-link" href="${linkUrl || '#'}" target="_blank" rel="noopener" onclick="event.stopPropagation();">${item.title}</a>${linkBadge}
      </td>
      <td class="col-scope"><span class="scope-tag">${item.scope || '-'}</span></td>
      <td class="col-sop">${item.sop_flag ? '★' : ''}</td>
    `;

    tr.addEventListener('click', () => selectItem(item.id));
    tbody.appendChild(tr);
  });
}

/* ---------------- 항목 선택 → 요약 + Gap분석 로드 ---------------- */
function selectItem(id) {
  state.selectedId = id;
  renderTable();
  const item = state.items.find(i => i.id === id);
  renderSummary(item);
  renderGap(item);
}

function renderSummary(item) {
  const box = $('#summaryBody');
  if (!item) { box.innerHTML = `<p class="empty-state">항목을 선택하면 요약이 표시됩니다.</p>`; return; }

  box.innerHTML = `
    <div class="summary-title">${item.title}</div>
    <div class="summary-meta">${item.agency_kr || ''} · ${item.reg_no || ''} · 고시일 ${item.published_date || '-'} · 시행일 ${item.effective_date || '-'}</div>
    <div class="summary-text">${item.summary || '요약 정보가 아직 없습니다.'}</div>
    <div class="summary-flags">
      <span class="flag-pill">적용범위: ${item.scope || '-'}</span>
      ${item.sop_flag ? '<span class="flag-pill sop">★ SOP 반영 검토 필요</span>' : ''}
      ${!item.verified ? '<span class="flag-pill unverified">원문 미확인 - 재검증 필요</span>' : ''}
    </div>
  `;
}

async function renderGap(item) {
  const box = $('#gapBody');
  if (!item) { box.innerHTML = `<p class="empty-state">항목을 선택하면 Gap 분석 결과가 표시됩니다.</p>`; return; }
  if (!item.gap_id) {
    box.innerHTML = `<p class="empty-state">이 항목은 아직 원문 대조(Gap 분석) 데이터가 준비되지 않았습니다. 다음 크롤링 주기에 원문이 확보되면 자동으로 생성됩니다.</p>`;
    return;
  }

  let gap;
  try {
    const res = await fetch(`data/gap/${item.gap_id}.json`, { cache: 'no-store' });
    gap = await res.json();
  } catch (e) {
    box.innerHTML = `<p class="empty-state">Gap 분석 데이터를 불러오지 못했습니다 (${item.gap_id}).</p>`;
    return;
  }

  let html = '';
  if (gap.is_sample) {
    html += `<div class="gap-disclaimer">⚠ ${gap.disclaimer}</div>`;
  }

  html += `
    <div class="gap-header-bar">
      <div><span class="old-label">◀ ${gap.old_version_label}</span></div>
      <div>${gap.regulation_title || ''}</div>
      <div><span class="new-label">${gap.new_version_label} ▶</span></div>
    </div>
  `;

  (gap.sections || []).forEach(sec => {
    html += `<div class="gap-section">`;
    html += `<div class="gap-section-title"><span>${sec.section_title}</span><span class="gap-status-tag ${sec.status}">${statusLabel(sec.status)}</span></div>`;
    html += `<div class="gap-block-wrap">`;
    (sec.blocks || []).forEach(b => {
      if (b.type === 'unchanged_collapsed') {
        html += `<div class="gap-collapsed">⋯ 동일 내용 생략 (${b.note || '변경 없음'}) ⋯</div>`;
      } else if (b.type === 'unchanged') {
        html += `<span class="gap-unchanged">${escapeHtml(b.text)}</span>`;
      } else if (b.type === 'deleted') {
        html += `<span class="gap-deleted">${escapeHtml(b.text)}</span>`;
      } else if (b.type === 'added') {
        html += `<span class="gap-added">${escapeHtml(b.text)}</span>`;
      } else if (b.type === 'na') {
        html += `<span class="gap-na">${b.note || 'N.A.'}</span>`;
      }
    });
    html += `</div></div>`;
  });

  box.innerHTML = html;
}

function statusLabel(status) {
  return { changed: '일부 변경', new: '신규 제정', unchanged: '변경 없음' }[status] || status;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

/* ---------------- 엑셀 다운로드 (현재 필터 기준) ---------------- */
function downloadXlsx() {
  const rows = state.filtered.map((item, idx) => ({
    'No.': idx + 1,
    '고시일 Published Date': item.published_date || '',
    '시행일 Effectiveness Date': item.effective_date || '',
    '발행처 Published by': item.agency_kr || item.publisher || '',
    '규격 및 가이던스 번호 Regulation & Guidance No.': item.reg_no || '',
    '제목 Title': item.title || '',
    '내용요약 Summary': item.summary || '',
    '적용 범위 Scope': item.scope || '',
    'SOP': item.sop_flag ? '★' : '',
    '원문 링크': item.source_type === 'direct' ? item.source_url : item.fallback_url,
    '검증상태': item.verified ? '확인됨' : '미확인'
  }));

  const ws = XLSX.utils.json_to_sheet(rows);
  ws['!cols'] = [
    { wch: 5 }, { wch: 12 }, { wch: 12 }, { wch: 16 }, { wch: 26 },
    { wch: 46 }, { wch: 50 }, { wch: 12 }, { wch: 6 }, { wch: 40 }, { wch: 10 }
  ];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');

  const ym = state.selectedMonthIdx > 0 ? state.months[state.selectedMonthIdx - 1] : 'ALL';
  XLSX.writeFile(wb, `국내외_규격_및_가이던스_업데이트_검토대장_${ym}.xlsx`);
}

init();
