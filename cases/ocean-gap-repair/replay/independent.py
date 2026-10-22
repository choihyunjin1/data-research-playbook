"""Independent audit. Does not import the frozen selector, predictor or analyzer.

Rebuilds extracted-hourly values, every case/choice, date-equal metrics and
calendar-block intervals and harm-avoidance accounting. Only this script and its JSON receipt are written.
The original one-off provenance checks are replaced by portable replay checks;
independent numerical formulas remain unchanged. Invoked by the replay entry.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd

from .context import ROOT, SOURCE, CASE_ROOT, CONTRACT_SHA
NAMES = ('remaining', 'temporal', 'depth', 'bridge', 'selected')
GAPS = (1, 3, 6, 12, 24)
TOL = 2e-11


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def close_arrays(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape
    assert np.array_equal(np.isnan(a), np.isnan(b)), 'NaN pattern differs'
    finite = np.isfinite(a) & np.isfinite(b)
    assert np.array_equal(np.isfinite(a), np.isfinite(b)), 'Finite pattern differs'
    error = float(np.max(np.abs(a[finite] - b[finite]))) if finite.any() else 0.
    assert error < TOL, error
    return error


def linear_pair(left, right, count):
    return np.linspace(left, right, count + 2)[1:-1]


def local_choice(observed, gap_start, gap_size, depths):
    """Use only disjoint observed probe blocks, never the true hidden target."""
    assert np.isnan(observed[gap_start:gap_start + gap_size, 1]).all()
    upper_weight = (depths[2] - depths[1]) / (depths[2] - depths[0])
    step = gap_size + 2
    groups = {'left': [], 'right': []}
    used_intervals = []
    for j in range(168 // step):
        for side in ('left', 'right'):
            begin = gap_start - (j + 1) * step if side == 'left' else gap_start + gap_size + j * step
            end = begin + step
            assert end <= gap_start or begin >= gap_start + gap_size
            assert begin >= gap_start - 168 and end <= gap_start + gap_size + 168
            block = observed[begin:end]
            if begin < 0 or end > len(observed) or not np.isfinite(block).all():
                continue
            assert len(block) == step
            mixed = upper_weight * block[:, 0] + (1 - upper_weight) * block[:, 2]
            straight = linear_pair(block[0, 1], block[-1, 1], gap_size)
            # Independent equivalent form: depth interpolation plus an endpoint
            # interpolation of target-minus-depth residuals.
            corrected = mixed[1:-1] + linear_pair(block[0, 1] - mixed[0], block[-1, 1] - mixed[-1], gap_size)
            err_t = np.sum(straight - block[1:-1, 1]) / 24
            err_b = np.sum(corrected - block[1:-1, 1]) / 24
            contribution = np.sum(corrected - straight) / 24
            groups[side].append((err_b * err_b - err_t * err_t,
                                 contribution * contribution, -2 * contribution * err_t))
            used_intervals.append((side, begin, end))
    for side in groups:
        intervals = sorted((a, b) for s, a, b in used_intervals if s == side)
        assert all(left[1] <= right[0] for left, right in zip(intervals, intervals[1:]))
    meta = {}
    enough, gains = [], []
    for side, values in groups.items():
        mean = np.mean(values, axis=0) if values else np.full(3, np.nan)
        meta.update({side + '_n': len(values), side + '_delta': mean[0],
                     side + '_energy': mean[1], side + '_match': mean[2]})
        enough.append(len(values) >= 4)
        gains.append(mean[0] < -1e-12)
    choice = 'bridge' if all(enough) and all(gains) else 'temporal'
    if choice == 'bridge':
        reason = 'both_sides_improved'
    elif not all(enough):
        reason = 'insufficient_context'
    elif any(gains):
        reason = 'sides_disagree'
    else:
        reason = 'no_two_sided_gain'
    meta['reason'] = reason
    return choice, meta, len(used_intervals)


def predict_separately(masked_day, start, size, depths):
    assert masked_day.shape == (26, 3)
    begin, end = start + 1, start + size + 1
    assert np.isnan(masked_day[begin:end, 1]).all()
    w_top = (depths[2] - depths[1]) / (depths[2] - depths[0])
    mix = w_top * masked_day[:, 0] + (1 - w_top) * masked_day[:, 2]
    time = linear_pair(masked_day[begin - 1, 1], masked_day[end, 1], size)
    depth = mix[begin:end]
    support = bool(np.isfinite(mix[[begin - 1, end]]).all())
    corrected = depth + linear_pair(masked_day[begin - 1, 1] - mix[begin - 1], masked_day[end, 1] - mix[end], size) if support else time.copy()
    known = masked_day[1:25, 1]
    remaining = np.mean(known[np.isfinite(known)]) if size < 24 else np.nan
    fills = {'temporal': time, 'depth': depth, 'bridge': corrected,
             'remaining': np.full(size, remaining)}
    means = {}
    for name, values in fills.items():
        reconstructed = known.copy()
        reconstructed[start:start + size] = values
        means[name] = reconstructed.mean() if size < 24 or name != 'remaining' else np.nan
    return means, fills, support



def table_check(expected, filename, keys, categorical=()):
    original = pd.read_csv(ROOT / filename, float_precision='round_trip')
    a = expected.set_index(keys).sort_index()
    b = original.set_index(keys).sort_index()
    assert a.index.equals(b.index), (filename, 'row keys')
    assert set(a.columns) == set(b.columns), (filename, a.columns, b.columns)
    for col in categorical:
        assert (a[col] == b[col]).all(), (filename, col)
    numeric = [col for col in a.columns if col not in categorical]
    return close_arrays(a[numeric], b[numeric]), len(a), len(a) * len(numeric)


def metrics_table(cases, extra=()):
    rows = []
    for keys, subset in cases.groupby(['gap_hours', *extra]):
        keys = keys if isinstance(keys, tuple) else (keys,)
        identity = dict(zip(['gap_hours', *extra], keys))
        for name in NAMES:
            finite = np.isfinite(subset[name + '_error'])
            sub = subset.loc[finite]
            daily = []
            for _, day in sub.groupby('date'):
                e = day[name + '_error'].to_numpy()
                daily.append([np.mean(e ** 2), np.mean(abs(e)), np.mean(e),
                              np.mean(day[name + '_point_mse'])])
            avg = np.mean(daily, axis=0) if daily else np.full(4, np.nan)
            rows.append({**identity, 'method': name, 'dates': subset.date.nunique(),
                         'valid_dates': sub.date.nunique(), 'cases': len(subset), 'valid_cases': len(sub),
                         'rmse': np.sqrt(avg[0]), 'mae': avg[1], 'bias': avg[2], 'point_rmse': np.sqrt(avg[3])})
    return pd.DataFrame(rows)


def resample_independently(daily, first, last, block, reps):
    """Explicit paired calendar block draw; no producer's resampling functions."""
    count_days = (last - first).days
    total_blocks = (count_days + block - 1) // block
    block_ids = (pd.DatetimeIndex(pd.to_datetime(daily.index, utc=True)) - first).days // block
    counts = np.zeros(total_blocks)
    totals = np.zeros((total_blocks, len(daily.columns)))
    for index, row in zip(block_ids, daily.to_numpy()):
        counts[index] += 1
        totals[index] += row
    rng = np.random.default_rng(20261022)
    output = []
    for _ in range(reps):
        chosen = rng.integers(0, total_blocks, total_blocks)
        divisor = np.sum(counts[chosen])
        if divisor:
            output.append(np.sum(totals[chosen], axis=0) / divisor)
    return np.array(output), count_days, total_blocks, int(np.count_nonzero(counts))


def harm_tables(c):
    """Arithmetic uses stored case errors AFTER independent reconstruction passed.
    This preserves the frozen exact D>0/D<0 tie contract at floating-point zero.
    All ratios and contributions use explicit date-equal case weights.
    """
    all_rows, by_reason, impacts, daily_tables = [], [], [], {}
    identity_max = 0.
    for size, g in c.groupby('gap_hours'):
        dates = g.date.to_numpy()
        weight = 1. / g.date.nunique() / g.groupby('date').date.transform('size').to_numpy()
        d = g.bridge_error.to_numpy() ** 2 - g.temporal_error.to_numpy() ** 2
        time = g.applied.to_numpy() == 'temporal'
        harmful, helpful = d > 0, d < 0
        avg = lambda v: float(np.dot(weight, np.asarray(v, float)))
        bad_mass, time_mass, avoided_mass = avg(harmful), avg(time), avg(time & harmful)
        avoided = np.where(time & harmful, d, 0.)
        missed = np.where(time & helpful, -d, 0.)
        retained_bad = np.where(~time & harmful, d, 0.)
        retained_good = np.where(~time & helpful, -d, 0.)
        net = g.selected_error.to_numpy() ** 2 - g.bridge_error.to_numpy() ** 2
        identity_max = max(identity_max, close_arrays(net, missed - avoided))
        daily = pd.DataFrame({'date': dates, 'avoided_harm': avoided, 'missed_gain': missed,
                              'retained_harm': retained_bad, 'retained_gain': retained_good,
                              'net_vs_bridge': net}).groupby('date').mean()
        daily_tables[int(size)] = daily
        all_rows.append({'gap_hours': size, 'priority': 'primary' if size in (6, 12, 24) else 'secondary',
                         'cases': len(g), 'dates': g.date.nunique(), 'harmful_bridge_cases': int(harmful.sum()),
                         'helpful_bridge_cases': int(helpful.sum()), 'tie_cases': int((d == 0).sum()),
                         'time_cases': int(time.sum()), 'avoided_harm_cases': int((time & harmful).sum()),
                         'missed_gain_cases': int((time & helpful).sum()), 'retained_harm_cases': int((~time & harmful).sum()),
                         'harm_recall': avoided_mass / bad_mass if bad_mass else np.nan,
                         'time_choice_precision': avoided_mass / time_mass if time_mass else np.nan,
                         'time_selection_share': time_mass, 'avoided_harm': avg(avoided),
                         'missed_gain': avg(missed), 'retained_harm': avg(retained_bad),
                         'retained_gain': avg(retained_good), 'net_vs_bridge': avg(net)})
        reason_total = np.zeros(len(g), dtype=int)
        for reason in ('no_two_sided_gain', 'sides_disagree', 'insufficient_context', 'missing_bridge_boundary'):
            chosen = time & (g.application_reason.to_numpy() == reason)
            reason_total += chosen
            mass, good = avg(chosen), avg(chosen & harmful)
            ah, mg = avg(np.where(chosen & harmful, d, 0)), avg(np.where(chosen & helpful, -d, 0))
            by_reason.append({'gap_hours': size, 'reason': reason,
                              'reason_class': 'evidence' if reason in ('no_two_sided_gain', 'sides_disagree') else 'unavailable_input',
                              'full_cohort_cases': len(g), 'time_cases': int(chosen.sum()),
                              'avoided_harm_cases': int((chosen & harmful).sum()), 'missed_gain_cases': int((chosen & helpful).sum()),
                              'full_cohort_time_share': mass, 'time_choice_precision': good / mass if mass else np.nan,
                              'harm_recall_contribution': good / bad_mass if bad_mass else np.nan,
                              'avoided_harm': ah, 'missed_gain': mg, 'net_vs_bridge': mg - ah})
        assert np.array_equal(reason_total, time.astype(int)), 'Every applied-time case must have one reason'
        for label, mask in [('chosen_helped', ~time & helpful), ('chosen_hurt', ~time & harmful),
                            ('time_avoided_harm', time & harmful), ('time_missed_gain', time & helpful)]:
            impacts.append({'gap_hours': size, 'category': label, 'cases': int(mask.sum()),
                            'full_cohort_delta_contribution': avg(np.where(mask, d, 0))})
    return pd.DataFrame(all_rows), pd.DataFrame(by_reason), pd.DataFrame(impacts), daily_tables, identity_max


def main():
    # Independent calculation, not a second experiment. No frozen imports.
    site, result = read_json('site.json'), read_json('result.json')
    first_read = read_json('source/extraction-read.json')
    core_sha = '6ae98feb21786c52ccc15d7f344e2f340b2c3a2a1bbd5ad18e7d9fa5a7f3a5f0'
    choice_sha = 'c64514bbafa145509472589cf708738117f18fd302f121816f96579b5dbbce0e'
    assert digest(CASE_ROOT / 'frozen/method.py') == core_sha
    assert digest(CASE_ROOT / 'frozen/selector.py') == choice_sha
    assert digest(SOURCE) == site['source_sha256'] == first_read['source_sha256']
    assert first_read['replay_contract_sha256'] == result['replay_contract_sha256'] == CONTRACT_SHA
    assert first_read['historical_replay'] and not first_read['new_holdout']
    assert pd.Timestamp(first_read['at_utc']) < pd.Timestamp(result['at_utc'])
    first, last = pd.Timestamp(site['eval_start_utc']), pd.Timestamp(site['eval_end_exclusive_utc'])
    query_first, query_last = pd.Timestamp(site['source_query_start_utc']), pd.Timestamp(site['source_query_end_exclusive_utc'])
    depths = np.array(site['depths_m'], float)
    assert np.array_equal(depths, [33., 44., 55.])
    h = pd.read_csv(ROOT / 'hourly.csv', float_precision='round_trip')
    times = pd.DatetimeIndex(pd.to_datetime(h.time_utc, utc=True))
    assert times.equals(pd.date_range(query_first, query_last, inclusive='left', freq='h'))
    assert first - query_first >= pd.Timedelta(days=7) and query_last - last >= pd.Timedelta(days=7)
    values = h[['top', 'target', 'bottom']].to_numpy(float)
    assert digest(ROOT / 'hourly.csv') == result['hourly_sha256']

    records = pd.read_csv(ROOT / 'source/selected-records.csv', float_precision='round_trip')
    records['time_utc'] = pd.to_datetime(records.time_utc, utc=True)
    assert set(records.instrument_index) <= set(site['instrument_indices'])
    duplicates = records.duplicated(['time_utc', 'depth_m'], keep=False)
    assert np.array_equal(duplicates, records.excluded_duplicate)
    rebuilt = records.loc[~duplicates].pivot(index='time_utc', columns='depth_m', values='temperature_c')
    rebuilt = rebuilt.reindex(index=times, columns=depths)
    extraction_error = close_arrays(rebuilt.to_numpy(), values)
    quality = read_json('source/extraction-quality.json')
    assert len(records) == quality['selected_rows'] == first_read['rows_requested']
    assert int(duplicates.sum()) == quality['duplicate_rows_excluded']

    rows, eligibility = [], []
    probe_count, mutation_count, mutation_seen = 0, 0, set()
    for day in pd.date_range(first, last, inclusive='left', freq='D'):
        day_index = times.get_loc(day)
        raw = values[day_index - 1:day_index + 25]
        complete = bool(np.isfinite(raw[1:25]).all())
        edges = bool(np.isfinite(raw[[0, 25], 1]).all())
        date = day.strftime('%Y-%m-%d')
        eligibility.append((date, complete and edges, complete, edges))
        if not (complete and edges):
            continue
        truth = raw[1:25, 1].copy()
        for size in GAPS:
            for start in range(0, 24, size):
                global_begin = day_index + start
                local = values[global_begin - 168:global_begin + size + 168].copy()
                local[168:168 + size, 1] = np.nan
                choice, metadata, used = local_choice(local, 168, size, depths)
                probe_count += used
                if (size, choice) not in mutation_seen:
                    changed = local.copy()
                    changed[168:168 + size] = [1e9, -1e9, -1e9]
                    changed[168:168 + size, 1] = np.nan
                    other, info, _ = local_choice(changed, 168, size, depths)
                    assert other == choice and info['reason'] == metadata['reason']
                    for key in metadata:
                        if key != 'reason':
                            close_arrays([info[key]], [metadata[key]])
                    mutation_seen.add((size, choice))
                    mutation_count += 1
                masked = raw.copy()
                masked[start + 1:start + size + 1, 1] = np.nan
                means, fills, supported = predict_separately(masked, start, size, depths)
                applied = choice if supported else 'temporal'
                means['selected'], fills['selected'] = means[applied], fills[applied]
                record = {'date': date, 'gap_hours': size, 'start': start, 'truth_daily': truth.mean(),
                          'action': choice, 'applied': applied, 'bridge_supported': supported,
                          'application_reason': 'missing_bridge_boundary' if choice == 'bridge' and not supported else metadata['reason'],
                          **metadata}
                for name in NAMES:
                    record[name + '_mean'] = means[name]
                    record[name + '_error'] = means[name] - truth.mean()
                    record[name + '_point_mse'] = np.mean(np.square(fills[name] - truth[start:start + size]))
                rows.append(record)
    independent = pd.DataFrame(rows)
    assert not independent.empty, 'No eligible dates: report unevaluable; do not fabricate pass'
    categories = ('action', 'applied', 'bridge_supported', 'reason', 'application_reason')
    case_error, case_rows, fields = table_check(independent, 'cases.csv', ['date', 'gap_hours', 'start'], categories)
    expected_eligibility = pd.DataFrame(eligibility, columns=['date', 'eligible', 'complete_day', 'target_edges'])
    pd.testing.assert_frame_equal(expected_eligibility, pd.read_csv(ROOT / 'day-eligibility.csv'))
    assert len(independent) == result['cases']
    assert independent.date.nunique() == result['eligible_dates']
    metrics = metrics_table(independent)
    metric_error, _, _ = table_check(metrics, 'overall.csv', ['gap_hours', 'method'])
    monthly = metrics_table(independent.assign(month=independent.date.str[:7]), ('month',))
    monthly_error, _, _ = table_check(monthly, 'monthly.csv', ['gap_hours', 'month', 'method'])
    stats = metrics.set_index(['gap_hours', 'method'])
    selections = pd.read_csv(ROOT / 'selection.csv').set_index('gap_hours')
    for size, group in independent.groupby('gap_hours'):
        expected = {'cases': len(group), 'bridge_chosen': int(group.action.eq('bridge').sum()),
                    'bridge_applied': int(group.applied.eq('bridge').sum()), 'bridge_rate': group.applied.eq('bridge').mean(),
                    'missing_bridge_boundary': int(group.application_reason.eq('missing_bridge_boundary').sum()),
                    **group.reason.value_counts().to_dict()}
        for key, value in expected.items():
            close_arrays([value], [selections.loc[size, key]])

    # Use stored exact errors for the strict floating-point sign contract only,
    # after independent reconstruction of those same errors has passed.
    recorded = pd.read_csv(ROOT / 'cases.csv', float_precision='round_trip')
    harm, reasons, impact, harm_daily, identity_max = harm_tables(recorded)
    harm_error, harm_rows, _ = table_check(harm, 'harm-diagnostics.csv', ['gap_hours'], ('priority',))
    reason_error, reason_rows, _ = table_check(reasons, 'harm-by-reason.csv', ['gap_hours', 'reason'], ('reason_class',))
    impact_error, _, _ = table_check(impact, 'selection-impact.csv', ['gap_hours', 'category'])

    interval_rows, harm_interval_rows, occupied = [], [], {}
    for size, group in independent.groupby('gap_hours'):
        for baseline in ('temporal', 'bridge', 'depth', 'remaining'):
            if size == 24 and baseline == 'remaining':
                continue
            daily = (group[['selected_error', baseline + '_error']] ** 2).groupby(group.date).mean()
            means = daily.mean().to_numpy()
            for block, reps in ((7, 2000), (30, 1000)):
                dist, days, blocks, nonempty = resample_independently(daily, first, last, block, reps)
                occupied[str(block)] = nonempty
                delta_rmse = np.sqrt(dist[:, 0]) - np.sqrt(dist[:, 1])
                delta_mse = dist[:, 0] - dist[:, 1]
                lo, hi = np.quantile(delta_rmse, [.025, .975])
                ml, mh = np.quantile(delta_mse, [.025, .975])
                actual = np.sqrt(means)
                interval_rows.append({'gap_hours': size, 'baseline': baseline, 'block_days': block,
                                      'calendar_days': days, 'calendar_blocks': blocks, 'requested_replicates': reps,
                                      'replicates': len(dist), 'rmse_delta': actual[0] - actual[1],
                                      'ci95_low': lo, 'ci95_high': hi, 'mse_delta': means[0] - means[1],
                                      'mse_ci95_low': ml, 'mse_ci95_high': mh,
                                      'percent_change': 100 * (actual[0] / actual[1] - 1) if actual[1] else np.nan})
        daily = harm_daily[int(size)][['avoided_harm', 'missed_gain', 'net_vs_bridge']]
        for block, reps in ((7, 2000), (30, 1000)):
            dist, days, blocks, _ = resample_independently(daily, first, last, block, reps)
            identity_max = max(identity_max, close_arrays(dist[:, 2], dist[:, 1] - dist[:, 0]))
            for index, name in enumerate(daily.columns):
                lo, hi = np.quantile(dist[:, index], [.025, .975])
                harm_interval_rows.append({'gap_hours': size, 'quantity': name, 'block_days': block,
                                           'calendar_days': days, 'calendar_blocks': blocks,
                                           'requested_replicates': reps, 'replicates': len(dist),
                                           'mse_contribution': float(daily[name].mean()), 'ci95_low': lo, 'ci95_high': hi})
    ci_error, ci_rows, _ = table_check(pd.DataFrame(interval_rows), 'uncertainty.csv', ['gap_hours', 'baseline', 'block_days'])
    harm_ci_error, harm_ci_rows, _ = table_check(pd.DataFrame(harm_interval_rows), 'harm-uncertainty.csv', ['gap_hours', 'quantity', 'block_days'])

    comparisons = []
    for size in GAPS:
        v = stats.loc[size, 'rmse']
        hr = harm[harm.gap_hours.eq(size)].iloc[0]
        comparisons.append({'gap_hours': size, 'selected_rmse': float(v['selected']),
                            'vs_temporal_percent': float(100 * (v['selected'] / v['temporal'] - 1)),
                            'vs_fixed_bridge_percent': float(100 * (v['selected'] / v['bridge'] - 1)),
                            'vs_depth_percent': float(100 * (v['selected'] / v['depth'] - 1)),
                            'harm_recall': float(hr.harm_recall) if np.isfinite(hr.harm_recall) else None,
                            'time_choice_precision': float(hr.time_choice_precision) if np.isfinite(hr.time_choice_precision) else None,
                            'time_selection_share': float(hr.time_selection_share),
                            'avoided_harm': float(hr.avoided_harm), 'missed_gain': float(hr.missed_gain),
                            'net_mse_vs_bridge': float(hr.net_vs_bridge),
                            'evidence_only_net_mse_vs_bridge': float(reasons.loc[reasons.gap_hours.eq(size) & reasons.reason_class.eq('evidence'), 'net_vs_bridge'].sum()),
                            'unavailable_input_net_mse_vs_bridge': float(reasons.loc[reasons.gap_hours.eq(size) & reasons.reason_class.eq('unavailable_input'), 'net_vs_bridge'].sum())})
    output = {'status': 'PASS_WITH_INTERPRETIVE_LIMITS', 'at_utc': datetime.now(timezone.utc).isoformat(),
              'independent_of_frozen_implementation': True, 'new_training_or_rule_tuning': False,
              'scope': 'No frozen imports. Rebuild hourly from extracted records, every case choice/mean/point MSE, overall/monthly metrics, harm/reasons/accounting and all CI. Exact sign harm arithmetic uses replayed case errors after independent reconstruction passes. Raw snapshot and extraction hashes are checked separately against historical expectations.',
              'source_records': len(records), 'hourly_cells_checked': int(values.size),
              'calendar_evaluation_days': (last - first).days, 'eligible_dates': independent.date.nunique(),
              'first_eligible': independent.date.min(), 'last_eligible': independent.date.max(),
              'eligible_months': independent[['date']].drop_duplicates().date.str[:7].value_counts().sort_index().to_dict(),
              'cases': case_rows, 'numeric_case_fields': fields, 'categorical_case_fields': case_rows * len(categories),
              'probe_blocks_externality_checks': probe_count, 'mask_mutation_checks': mutation_count,
              'historical_replay': True, 'new_holdout': False,
              'core_sha256': core_sha, 'selector_sha256': choice_sha, 'replay_contract_sha256': CONTRACT_SHA,
              'max_absolute_errors': {'selected_records_to_hourly': extraction_error, 'case_numeric': case_error,
                                      'overall': metric_error, 'monthly': monthly_error, 'harm': harm_error,
                                      'reasons': reason_error, 'impact': impact_error, 'rmse_mse_CI': ci_error,
                                      'harm_CI': harm_ci_error, 'harm_identity': identity_max},
              'harm_rows': harm_rows, 'reason_rows': reason_rows, 'CI_rows': ci_rows, 'harm_CI_rows': harm_ci_rows,
              'occupied_calendar_blocks': occupied, 'comparisons': comparisons,
              'hourly_sha256': digest(ROOT / 'hourly.csv'), 'review_script_sha256': digest(Path(__file__))}
    (ROOT / 'independent-check.json').write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return output


if __name__ == '__main__':
    main()

