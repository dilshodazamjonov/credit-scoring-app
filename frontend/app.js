/* ─────────────────────────────────────────────────────────────
   CreditCore · Loan Portal · app.js
   All application logic: schema, form generation, prefill,
   submission, and result rendering.
───────────────────────────────────────────────────────────── */

'use strict';

/* ── API Config ──────────────────────────────────────────────── */
const API_URL = 'http://localhost:3000/apply';

/* ── Model Schema ────────────────────────────────────────────── */
const MODEL_SCHEMA = {
  model_name: 'catboost_credit_risk',
  threshold: 0.4762968274967872,
  required_features_count: 20,
  features: [
    { name: 'AMT_ANNUITY',                   type: 'number' },
    { name: 'AMT_GOODS_PRICE',               type: 'number' },
    { name: 'DAYS_BIRTH',                    type: 'number' },
    { name: 'DAYS_EMPLOYED',                 type: 'number' },
    { name: 'DAYS_LAST_PHONE_CHANGE',        type: 'number' },
    { name: 'EXT_SOURCE_1',                  type: 'number' },
    { name: 'EXT_SOURCE_2',                  type: 'number' },
    { name: 'EXT_SOURCE_3',                  type: 'number' },
    { name: 'OCCUPATION_TYPE',               type: 'string' },
    { name: 'REGION_RATING_CLIENT_W_CITY',   type: 'number' },
    { name: 'active_rate',                   type: 'number' },
    { name: 'approval_rate',                 type: 'number' },
    { name: 'avg_days_credit',               type: 'number' },
    { name: 'avg_debt_ratio',                type: 'number' },
    { name: 'avg_payment_ratio_y',           type: 'number' },
    { name: 'avg_utilization',               type: 'number' },
    { name: 'late_rate',                     type: 'number' },
    { name: 'recent_credit_days',            type: 'number' },
    { name: 'rejection_rate',                type: 'number' },
    { name: 'total_paid',                    type: 'number' },
  ],
};

/* ── Field Display Metadata ──────────────────────────────────── */
const FIELD_META = {
  AMT_ANNUITY:                  { label: 'Annuity Amount',         placeholder: 'e.g. 15000' },
  AMT_GOODS_PRICE:              { label: 'Goods / Property Price', placeholder: 'e.g. 180000' },
  DAYS_BIRTH:                   { label: 'Days since Birth',       placeholder: 'e.g. -14600 (negative)' },
  DAYS_EMPLOYED:                { label: 'Days Employed',          placeholder: 'e.g. -3650 or 365243' },
  DAYS_LAST_PHONE_CHANGE:       { label: 'Days Since Phone Change',placeholder: 'e.g. -365 (negative)' },
  EXT_SOURCE_1:                 { label: 'External Score 1',       placeholder: '0.0 – 1.0' },
  EXT_SOURCE_2:                 { label: 'External Score 2',       placeholder: '0.0 – 1.0' },
  EXT_SOURCE_3:                 { label: 'External Score 3',       placeholder: '0.0 – 1.0' },
  OCCUPATION_TYPE:              { label: 'Occupation Type',        placeholder: '— Select —' },
  REGION_RATING_CLIENT_W_CITY:  { label: 'Region Rating (City)',   placeholder: '1, 2 or 3' },
  active_rate:                  { label: 'Active Credit Rate',     placeholder: '0.0 – 1.0' },
  approval_rate:                { label: 'Approval Rate',          placeholder: '0.0 – 1.0' },
  avg_days_credit:              { label: 'Avg Days Credit',        placeholder: 'e.g. -800' },
  avg_debt_ratio:               { label: 'Avg Debt Ratio',         placeholder: '0.0 – 1.0' },
  avg_payment_ratio_y:          { label: 'Avg Payment Ratio',      placeholder: '0.0 – 1.0' },
  avg_utilization:              { label: 'Avg Utilisation',        placeholder: '0.0 – 1.0' },
  late_rate:                    { label: 'Late Payment Rate',      placeholder: '0.0 – 1.0' },
  recent_credit_days:           { label: 'Recent Credit Days',     placeholder: 'e.g. -180 (negative)' },
  rejection_rate:               { label: 'Rejection Rate',         placeholder: '0.0 – 1.0' },
  total_paid:                   { label: 'Total Paid',             placeholder: 'e.g. 250000' },
};

/* ── Occupation Options ──────────────────────────────────────── */
const OCCUPATIONS = [
  'Accountants', 'Cleaning staff', 'Cooking staff', 'Core staff',
  'Drivers', 'HR staff', 'High skill tech staff', 'IT staff',
  'Laborers', 'Low-skill Laborers', 'Managers', 'Medicine staff',
  'Private service staff', 'Realty agents', 'Sales staff',
  'Secretaries', 'Security staff', 'Waiters/barmen staff',
];

/* ── Test Scenarios ──────────────────────────────────────────── */
/**
 * Values chosen to exercise the model at opposite ends.
 * GOOD  → all positive indicators (high EXT scores, long employment,
 *          low late/rejection rates, high approval).
 * RISK  → all negative indicators (low EXT scores, unemployed marker,
 *          high late/rejection rates, low approval).
 */
const SCENARIOS = {
  good: {
    AMT_ANNUITY:                 15000,
    AMT_GOODS_PRICE:             180000,
    DAYS_BIRTH:                  -14965,
    DAYS_EMPLOYED:               -3650,
    DAYS_LAST_PHONE_CHANGE:      -730,
    EXT_SOURCE_1:                0.83,
    EXT_SOURCE_2:                0.79,
    EXT_SOURCE_3:                0.76,
    OCCUPATION_TYPE:             'Accountants',
    REGION_RATING_CLIENT_W_CITY: 1,
    active_rate:                 0.55,
    approval_rate:               0.88,
    avg_days_credit:             -1400,
    avg_debt_ratio:              0.12,
    avg_payment_ratio_y:         0.97,
    avg_utilization:             0.22,
    late_rate:                   0.01,
    recent_credit_days:          -365,
    rejection_rate:              0.04,
    total_paid:                  280000,
  },
  risk: {
    AMT_ANNUITY:                 48000,
    AMT_GOODS_PRICE:             620000,
    DAYS_BIRTH:                  -11315,
    DAYS_EMPLOYED:               365243,       // unemployed sentinel
    DAYS_LAST_PHONE_CHANGE:      -25,
    EXT_SOURCE_1:                0.14,
    EXT_SOURCE_2:                0.19,
    EXT_SOURCE_3:                0.11,
    OCCUPATION_TYPE:             'Laborers',
    REGION_RATING_CLIENT_W_CITY: 3,
    active_rate:                 0.92,
    approval_rate:               0.18,
    avg_days_credit:             -180,
    avg_debt_ratio:              0.78,
    avg_payment_ratio_y:         0.28,
    avg_utilization:             0.91,
    late_rate:                   0.48,
    recent_credit_days:          -22,
    rejection_rate:              0.64,
    total_paid:                  12000,
  },
};

/* ── DOM Refs ────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);

const formCard    = $('form-card');
const resultCard  = $('result-card');
const loanForm    = $('loan-form');
const btnSubmit   = $('btn-submit');
const formError   = $('form-error');

/* ────────────────────────────────────────────────────────────── */
/*  FORM BUILDER                                                  */
/* ────────────────────────────────────────────────────────────── */

function buildForm() {
  const gridNum = $('grid-number');
  const gridStr = $('grid-string');
  let numCount = 0;

  MODEL_SCHEMA.features.forEach(feat => {
    const meta = FIELD_META[feat.name] || { label: feat.name, placeholder: '' };
    const wrapper = document.createElement('div');
    wrapper.className = 'field';

    const label = document.createElement('label');
    label.setAttribute('for', feat.name);
    label.textContent = meta.label;
    wrapper.appendChild(label);

    if (feat.type === 'string') {
      const sel = document.createElement('select');
      sel.id = feat.name;
      sel.name = feat.name;
      sel.required = true;

      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.disabled = true;
      placeholder.selected = true;
      placeholder.textContent = meta.placeholder || '— Select —';
      sel.appendChild(placeholder);

      OCCUPATIONS.forEach(occ => {
        const opt = document.createElement('option');
        opt.value = occ;
        opt.textContent = occ;
        sel.appendChild(opt);
      });

      wrapper.appendChild(sel);
      gridStr.appendChild(wrapper);
    } else {
      const input = document.createElement('input');
      input.type = 'number';
      input.id = feat.name;
      input.name = feat.name;
      input.step = 'any';
      input.required = true;
      input.placeholder = meta.placeholder || '';

      // Remove error class on user input
      input.addEventListener('input', () => input.classList.remove('error'));

      wrapper.appendChild(input);
      gridNum.appendChild(wrapper);
      numCount++;
    }
  });

  // Update field count label
  $('num-field-count') && ($('num-field-count').textContent = `${numCount} fields`);
}

/* ────────────────────────────────────────────────────────────── */
/*  PRE-FILL SCENARIOS                                            */
/* ────────────────────────────────────────────────────────────── */

function fillScenario(type) {
  const data = SCENARIOS[type];
  if (!data) return;

  MODEL_SCHEMA.features.forEach(feat => {
    const el = $(feat.name);
    if (!el) return;
    el.value = data[feat.name] ?? '';
    el.classList.remove('error');

    // Brief visual flash to signal update
    el.classList.add('filled');
    setTimeout(() => el.classList.remove('filled'), 600);
  });

  hideFormError();
}

/* ────────────────────────────────────────────────────────────── */
/*  VALIDATION                                                    */
/* ────────────────────────────────────────────────────────────── */

function validate() {
  let firstError = null;

  MODEL_SCHEMA.features.forEach(feat => {
    const el = $(feat.name);
    if (!el) return;

    const empty = el.value === '' || el.value === null;
    if (empty) {
      el.classList.add('error');
      if (!firstError) firstError = el;
    } else {
      el.classList.remove('error');
    }
  });

  if (firstError) {
    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
    firstError.focus();
  }

  return !firstError;
}

/* ────────────────────────────────────────────────────────────── */
/*  FORM SUBMISSION                                               */
/* ────────────────────────────────────────────────────────────── */

async function handleSubmit(e) {
  e.preventDefault();
  hideFormError();

  if (!validate()) return;

  // Build payload — all keys at root level as required by the API
  const payload = {};
  MODEL_SCHEMA.features.forEach(feat => {
    const el = $(feat.name);
    payload[feat.name] = feat.type === 'number' ? parseFloat(el.value) : el.value;
  });

  setLoading(true);

  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      throw new Error(`Server responded ${res.status}: ${text}`);
    }

    const data = await res.json();

    if (data.status && data.status !== 'success') {
      throw new Error(data.message || `Unexpected status: ${data.status}`);
    }

    // Short delay for perceived processing (feels more trustworthy)
    await sleep(420);

    setLoading(false);
    transitionToResult(data);

  } catch (err) {
    setLoading(false);
    showFormError(err);
  }
}

/* ────────────────────────────────────────────────────────────── */
/*  RESULT RENDERING                                              */
/* ────────────────────────────────────────────────────────────── */

function transitionToResult(data) {
  // 1. Fade form card out
  formCard.classList.add('exiting');

  setTimeout(() => {
    formCard.style.display = 'none';
    renderResult(data);
    resultCard.classList.add('show');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, 220);
}

function renderResult(data) {
  const { decision, probability, threshold } = data;
  const isApproved = decision === 'APPROVED';
  const pct   = (probability * 100);
  const tpct  = (threshold   * 100);
  const margin = Math.abs(probability - threshold) * 100;

  /* ── Top row ── */
  const icon = $('result-icon');
  icon.className = 'result-icon ' + (isApproved ? 'approved' : 'rejected');

  const decEl = $('result-decision');
  decEl.className = 'result-decision ' + (isApproved ? 'approved' : 'rejected');
  decEl.textContent = isApproved ? 'Application Approved' : 'Application Declined';

  $('result-sub').textContent = isApproved
    ? `Your risk score of ${fmtPct(pct)} is below the ${fmtPct(tpct)} threshold — you are eligible to proceed.`
    : `Your risk score of ${fmtPct(pct)} exceeds the ${fmtPct(tpct)} threshold — the assessed risk is too high.`;

  const badge = $('result-badge');
  badge.textContent = isApproved ? 'APPROVED' : 'DECLINED';
  badge.className = 'result-badge ' + (isApproved ? 'approved' : 'rejected');

  /* ── Stats ── */
  const scoreEl = $('stat-score');
  scoreEl.textContent = fmtPct(pct);
  scoreEl.style.color = isApproved ? 'var(--green)' : 'var(--red)';

  $('stat-thresh').textContent = fmtPct(tpct);

  const marginEl = $('stat-margin');
  marginEl.textContent = (isApproved ? '−' : '+') + fmtPct(margin);
  marginEl.style.color = isApproved ? 'var(--green)' : 'var(--red)';

  /* ── Risk meter ── */
  $('meter-readout').textContent = `${fmtPct(pct)} / ${fmtPct(tpct)} limit`;

  const fill = $('meter-fill');
  fill.className = 'meter-fill ' + (isApproved ? 'safe' : 'risky');
  // Width set with a slight delay to trigger CSS transition
  requestAnimationFrame(() => {
    fill.style.width = Math.min(pct, 100) + '%';
  });

  const pin = $('meter-pin');
  pin.style.left = Math.min(tpct, 100) + '%';
  $('meter-pin-label').textContent = fmtPct(tpct) + ' limit';
}

/* ────────────────────────────────────────────────────────────── */
/*  RESET                                                         */
/* ────────────────────────────────────────────────────────────── */

function resetApp() {
  // Reset meter fill immediately (no transition) before hiding
  const fill = $('meter-fill');
  fill.style.transition = 'none';
  fill.style.width = '0%';

  resultCard.classList.remove('show');

  setTimeout(() => {
    formCard.style.display = '';
    // Re-enable transition for next time
    fill.style.transition = '';

    requestAnimationFrame(() => {
      formCard.classList.remove('exiting');
    });

    loanForm.reset();
    document.querySelectorAll('.field input.error, .field select.error')
      .forEach(el => el.classList.remove('error'));
    hideFormError();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, 50);
}

/* ────────────────────────────────────────────────────────────── */
/*  UI HELPERS                                                    */
/* ────────────────────────────────────────────────────────────── */

function setLoading(on) {
  btnSubmit.disabled = on;
  btnSubmit.classList.toggle('loading', on);

  // Disable all inputs while loading
  document.querySelectorAll('#loan-form input, #loan-form select')
    .forEach(el => { el.disabled = on; });
}

function showFormError(err) {
  const isNetwork = err instanceof TypeError;
  formError.innerHTML = isNetwork
    ? `<strong>Could not reach the API</strong> at <code style="font-family:monospace;font-size:11px">${API_URL}</code>.
       Ensure your Go gateway is running and CORS is enabled.<br>
       <span style="opacity:.7;font-size:11.5px">${err.message}</span>`
    : `<strong>Error:</strong> ${err.message}`;
  formError.classList.add('show');
}

function hideFormError() {
  formError.classList.remove('show');
  formError.innerHTML = '';
}

function fmtPct(val) {
  return val.toFixed(2) + '%';
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/* ────────────────────────────────────────────────────────────── */
/*  EVENT LISTENERS                                               */
/* ────────────────────────────────────────────────────────────── */

loanForm.addEventListener('submit', handleSubmit);

$('btn-good').addEventListener('click', () => fillScenario('good'));
$('btn-risk').addEventListener('click', () => fillScenario('risk'));
$('btn-new').addEventListener('click', resetApp);

/* ────────────────────────────────────────────────────────────── */
/*  INIT                                                          */
/* ────────────────────────────────────────────────────────────── */

buildForm();