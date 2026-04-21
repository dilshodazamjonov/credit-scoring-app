/* ─────────────────────────────────────────────────────────────
   CreditCore · Loan Portal · app.js
   All application logic: schema fetching, form generation, 
   prefill, submission, and result rendering.
───────────────────────────────────────────────────────────── */

'use strict';

/* ── API Config ──────────────────────────────────────────────── */
const API_URL = 'http://localhost:3000/apply';
const CONFIG_URL = 'http://localhost:3000/config';

/* ── State ───────────────────────────────────────────────────── */
let MODEL_SCHEMA = null;

/* ── Field Display Metadata ──────────────────────────────────── */
// Used to provide nice labels/placeholders for known features.
// If the model returns a new feature not in this list, the app
// will automatically format its name (e.g., "NEW_FEATURE_1" -> "New Feature 1").
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
    DAYS_EMPLOYED:               365243,       
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
/*  INIT & CONFIG FETCH                                           */
/* ────────────────────────────────────────────────────────────── */

async function initApp() {
  try {
    const res = await fetch(CONFIG_URL);
    if (!res.ok) throw new Error("Gateway configuration unavailable");
    
    MODEL_SCHEMA = await res.json();
    buildForm();
  } catch (err) {
    showFormError(new Error("Could not connect to API. Is the Go Gateway running on port 3000?"));
  }
}

/* ────────────────────────────────────────────────────────────── */
/*  FORM BUILDER                                                  */
/* ────────────────────────────────────────────────────────────── */

function formatFallbackLabel(name) {
  return name.toLowerCase().split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function buildForm() {
  const gridNum = $('grid-number');
  const gridStr = $('grid-string');
  let numCount = 0;

  MODEL_SCHEMA.features.forEach(feat => {
    // Determine label: use mapped meta or format the raw variable name
    const fallbackLabel = formatFallbackLabel(feat.name);
    const meta = FIELD_META[feat.name] || { label: fallbackLabel, placeholder: '' };
    
    const wrapper = document.createElement('div');
    wrapper.className = 'field';

    const label = document.createElement('label');
    label.setAttribute('for', feat.name);
    label.textContent = meta.label;
    wrapper.appendChild(label);

    if (feat.type === 'string' || feat.type === 'object') {
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

      sel.addEventListener('change', () => sel.classList.remove('error'));
      wrapper.appendChild(sel);
      gridStr.appendChild(wrapper);
    } else {
      const input = document.createElement('input');
      input.type = 'number';
      input.id = feat.name;
      input.name = feat.name;
      input.step = 'any';
      input.required = true;
      input.placeholder = meta.placeholder || '0.00';

      input.addEventListener('input', () => input.classList.remove('error'));
      wrapper.appendChild(input);
      gridNum.appendChild(wrapper);
      numCount++;
    }
  });

  // Update dynamic counters
  if ($('num-field-count')) {
    $('num-field-count').textContent = `${numCount} fields`;
  }
  
  const modelTag = document.querySelector('.model-tag');
  if (modelTag) {
    modelTag.textContent = `CatBoost · ${MODEL_SCHEMA.features.length} features · threshold ${MODEL_SCHEMA.threshold.toFixed(4)}`;
  }
}

/* ────────────────────────────────────────────────────────────── */
/*  PRE-FILL SCENARIOS                                            */
/* ────────────────────────────────────────────────────────────── */

function fillScenario(type) {
  if (!MODEL_SCHEMA) return;
  const data = SCENARIOS[type];
  if (!data) return;

  MODEL_SCHEMA.features.forEach(feat => {
    const el = $(feat.name);
    if (!el) return;
    
    // Safely apply fallback values if the scenario dictionary doesn't map a new feature
    const val = data[feat.name];
    if (val !== undefined) {
      el.value = val;
    } else {
      el.value = (feat.type === 'number' || feat.type === 'float') ? 0 : '';
    }

    el.classList.remove('error');
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

  const payload = {};
  MODEL_SCHEMA.features.forEach(feat => {
    const el = $(feat.name);
    // Ensure numeric types are strictly parsed to avoid CatBoost casting errors
    const isNumeric = feat.type === 'number' || feat.type === 'float' || feat.type === 'int';
    payload[feat.name] = isNumeric ? parseFloat(el.value) : el.value;
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
  const fill = $('meter-fill');
  fill.style.transition = 'none';
  fill.style.width = '0%';

  resultCard.classList.remove('show');

  setTimeout(() => {
    formCard.style.display = '';
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
/*  BOOTSTRAP                                                     */
/* ────────────────────────────────────────────────────────────── */

initApp();