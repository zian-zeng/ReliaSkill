"""Strict verification: saved tables vs source main_results.csv files."""
import csv
from pathlib import Path

SOURCES = [
    ('Gemma2-2B',    'outputs/gemma2_2b_fast_results',    None),
    ('Gemma2-9B',    'outputs/gemma2_9b_fast_results',    None),
    ('Qwen2.5-1.5B', 'outputs/qwen_comparison_results',   None),
    ('Qwen2.5-7B',   'outputs/medium_overnight_real_gpu', {'raw_mcp', 'autoskill_base'}),
    ('Qwen2.5-7B',   'outputs/qwen25_7b_fast_results',
        {'human_written_skill_upper_bound', 'skill_prompt_boundary_first', 'skill_prompt_verbose_docs'}),
    ('Phi-3.5-mini', 'outputs/phi3_5_mini_fast_results',  None),
    ('Llama3.2-1B',  'outputs/llama3_1b_fast_results',    None),
    ('Llama3.1-8B',  'outputs/llama3_8b_fast_results',    None),
]
CONDS = [
    'raw_mcp', 'autoskill_base', 'human_written_skill_upper_bound',
    'skill_prompt_boundary_first', 'skill_prompt_verbose_docs',
]
# Source main_results.csv files still use the historical condition name.
# Saved tables use the paper-facing name. Map source -> saved.
NAME_MAP = {
    'human_written_skill_upper_bound': 'curated_schema_reference',
    'autoskill_base': 'generated_skill_base',
}
def saved_name(c):
    return NAME_MAP.get(c, c)
MODELS = ['Gemma2-2B', 'Gemma2-9B', 'Qwen2.5-1.5B', 'Qwen2.5-7B',
          'Phi-3.5-mini', 'Llama3.2-1B', 'Llama3.1-8B']

def norm(s):
    return round(float(s), 4)

truth = {}
for model, run_dir, only in SOURCES:
    csv_path = Path(run_dir) / 'reports' / 'main_results.csv'
    with csv_path.open(encoding='utf-8', newline='') as fh:
        rdr = csv.DictReader(fh)
        for row in rdr:
            if not row or not row.get('condition'):
                continue
            c = row['condition']
            if c not in CONDS:
                continue
            if only is not None and c not in only:
                continue
            truth[(model, c)] = (row['exact_match_rate'], row['routing_joint_exact_match_rate'])

print(f'TRUTH cells loaded from source CSVs: {len(truth)} (expect 35)')

def load_wide(path):
    d = {}
    with open(path, encoding='utf-8', newline='') as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        models_in_file = header[1:-1]
        for row in rdr:
            if not row or not row[0]:
                continue
            cond = row[0]
            for m, v in zip(models_in_file, row[1:-1]):
                d[(m, cond)] = v
            d[('__MEAN__', cond)] = row[-1]
    return d

struct_saved  = load_wide('outputs/tables/final_7_modal_comparsion_across_5_conditions_structured.csv')
routing_saved = load_wide('outputs/tables/final_7_modal_comparsion_across_5_conditions_routing.csv')

long_saved = {}
with open('outputs/tables/final_7_modal_comparsion_across_5_conditions_long.csv', encoding='utf-8', newline='') as fh:
    rdr = csv.DictReader(fh)
    for row in rdr:
        if not row or not row.get('model'):
            continue
        long_saved[(row['model'], row['condition'])] = (row['structured_exact_match'], row['routing_joint_exact'])

mismatches = []
for (model, cond), (em_truth, rt_truth) in truth.items():
    em_saved = struct_saved.get((model, saved_name(cond)))
    if em_saved is None or norm(em_saved) != norm(em_truth):
        mismatches.append(f'STRUCT wide ({model}, {cond}): saved={em_saved!r} truth={em_truth!r}')
    rt_saved = routing_saved.get((model, saved_name(cond)))
    if rt_saved is None or norm(rt_saved) != norm(rt_truth):
        mismatches.append(f'ROUTING wide ({model}, {cond}): saved={rt_saved!r} truth={rt_truth!r}')
    long_pair = long_saved.get((model, saved_name(cond)))
    if long_pair is None:
        mismatches.append(f'LONG ({model}, {cond}): missing in long.csv')
    elif norm(long_pair[0]) != norm(em_truth) or norm(long_pair[1]) != norm(rt_truth):
        mismatches.append(f'LONG ({model}, {cond}): saved={long_pair!r} truth=({em_truth!r}, {rt_truth!r})')

print()
print('=== Mean(7) column recomputation ===')
for cond in CONDS:
    em_vals = [norm(truth[(m, cond)][0]) for m in MODELS]
    rt_vals = [norm(truth[(m, cond)][1]) for m in MODELS]
    em_mean = round(sum(em_vals) / 7, 4)
    rt_mean = round(sum(rt_vals) / 7, 4)
    saved_em_mean = norm(struct_saved[('__MEAN__', saved_name(cond))])
    saved_rt_mean = norm(routing_saved[('__MEAN__', saved_name(cond))])
    print(f'  {cond}: struct mean saved={saved_em_mean} recomputed={em_mean} | routing mean saved={saved_rt_mean} recomputed={rt_mean}')
    if em_mean != saved_em_mean:
        mismatches.append(f'STRUCT Mean ({cond}): saved={saved_em_mean} recomputed={em_mean}')
    if rt_mean != saved_rt_mean:
        mismatches.append(f'ROUTING Mean ({cond}): saved={saved_rt_mean} recomputed={rt_mean}')

print()
print('=' * 65)
if mismatches:
    print(f'FOUND {len(mismatches)} MISMATCH(ES):')
    for m in mismatches:
        print('  ' + m)
else:
    print('ALL 35 CELLS + 10 MEAN VALUES MATCH SOURCE main_results.csv')
    print('  - structured wide csv: 35 cells verified')
    print('  - routing wide csv:    35 cells verified')
    print('  - long csv:            35 cells x 2 metrics verified')
    print('  - Mean(7) column:      10 values recomputed and verified')
print('=' * 65)
