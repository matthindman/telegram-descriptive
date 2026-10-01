"""Build the snapshot-identity graph; retain valid/all-target normalization variants."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.stats import spearmanr


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def entities(frame):
    ids = frame.chat_id
    assert (ids.dropna() == ids.dropna().astype('int64')).all()
    assert (ids.dropna().abs() < 2**53).all()
    return pd.Series(np.where(ids.notna(), 'chat:' + ids.fillna(0).astype('int64').astype(str),
                              'handle:' + frame.handle), index=frame.index)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    a = p.parse_args(); out = a.root / 'graph'; out.mkdir(exist_ok=True)
    raw = a.root.parent / 'channel_graph_2026-09-30/graph'
    valid = a.root.parent / 'channel_graph_filtered_2026-09-30/graph'
    cohort = pd.read_parquet(out / 'crawled_nodes.parquet')
    full = pd.read_parquet(raw / 'nodes_indexed.parquet')
    eligible = pd.read_parquet(valid / 'nodes_indexed.parquet', columns=['handle'])
    # The cohort export supplies the same snapshot identity plus isolated handles.
    known = full[['handle', 'chat_id']].merge(cohort[['handle', 'chat_id']], on='handle', how='outer', suffixes=('', '_cohort'))
    both = known.chat_id.notna() & known.chat_id_cohort.notna()
    assert (known.loc[both, 'chat_id'] == known.loc[both, 'chat_id_cohort']).all()
    known['chat_id'] = known.chat_id_cohort.combine_first(known.chat_id)
    known['entity_id'] = entities(known)
    identity = known.set_index('handle').entity_id
    cohort['entity_id'] = cohort.handle.map(identity)
    # HTTP time is a representative-row proxy, NOT a verified count timestamp.
    ordered = cohort.sort_values(['http_validated_at', 'last_crawled_at', 'handle'],
                                 ascending=[False, False, True], na_position='last')
    nodes = ordered.drop_duplicates('entity_id').sort_values('entity_id').reset_index(drop=True)
    nodes.insert(0, 'node_id', np.arange(len(nodes), dtype=np.int32))
    grouped = cohort.groupby('entity_id')
    for col, values in [('cohort_alias_count', grouped.size()),
                        ('subscribers_min', grouped.subscribers.min()),
                        ('subscribers_max', grouped.subscribers.max()),
                        ('subscriber_distinct_values', grouped.subscribers.nunique()),
                        ('recorded_visits', grouped.recorded_visits.sum()),
                        ('total_messages_processed', grouped.total_messages_processed.max())]:
        nodes[col] = nodes.entity_id.map(values)
    nodes['subscriber_conflict'] = nodes.subscriber_distinct_values > 1
    all_eligible = set(eligible.handle) | set(cohort.handle)
    aliases = known[known.handle.isin(all_eligible) & known.entity_id.isin(nodes.entity_id)].copy()
    aliases['node_id'] = aliases.entity_id.map(nodes.set_index('entity_id').node_id).astype('int32')
    aliases['in_original_cohort'] = aliases.handle.isin(cohort.handle)
    aliases['representative'] = aliases.handle.isin(nodes.handle)
    aliases[['node_id', 'entity_id', 'handle', 'in_original_cohort', 'representative']].to_parquet(out / 'aliases.parquet', index=False)
    cohort.to_parquet(out / 'alias_observations.parquet', index=False)

    def remap(frame):
        return pd.DataFrame({'source_entity': frame.source_handle.map(identity),
                             'target_entity': frame.target_handle.map(identity)})
    fe = pd.read_parquet(valid / 'edges.parquet', columns=['source_handle', 'target_handle'])
    ve = remap(fe); assert not ve.isna().any().any()
    loops_removed = int((ve.source_entity == ve.target_entity).sum())
    ve = ve[ve.source_entity != ve.target_entity].drop_duplicates()
    re = pd.read_parquet(raw / 'edges.parquet', columns=['source_handle', 'target_handle'])
    re = re[re.source_handle.isin(all_eligible)]
    ae = remap(re); assert not ae.isna().any().any()
    ae = ae[ae.source_entity != ae.target_entity].drop_duplicates()
    dv = ve.groupby('source_entity').size(); da = ae.groupby('source_entity').size()
    nodes['global_valid_outdegree'] = nodes.entity_id.map(dv).fillna(0).astype('int32')
    nodes['global_all_outdegree'] = nodes.entity_id.map(da).fillna(0).astype('int32')
    assert (nodes.global_all_outdegree >= nodes.global_valid_outdegree).all()
    ix = pd.Index(nodes.entity_id)
    s = ix.get_indexer(ve.source_entity); t = ix.get_indexer(ve.target_entity)
    mask = (s >= 0) & (t >= 0); s = s[mask].astype('int32'); t = t[mask].astype('int32')
    order = np.lexsort((t, s)); s = s[order]; t = t[order]
    d = nodes.global_valid_outdegree.to_numpy(); ad = nodes.global_all_outdegree.to_numpy()
    directed = pd.DataFrame({'source': s, 'target': t, 'weight_source_fractional': 1/d[s],
                             'weight_all_targets': 1/ad[s]})
    directed.to_parquet(out / 'directed_edges.parquet', index=False)
    shape = (len(nodes), len(nodes))
    b = sparse.csr_matrix((np.ones(len(s), dtype=np.uint8), (s, t)), shape=shape)
    f = sparse.csr_matrix((1/d[s], (s, t)), shape=shape)
    fa = sparse.csr_matrix((1/ad[s], (s, t)), shape=shape)
    u = b.maximum(b.T); w = f + f.T; wa = fa + fa.T
    pairs = sparse.triu(w, 1).tocoo()
    ue = pd.DataFrame({'source': pairs.row.astype('int32'), 'target': pairs.col.astype('int32'),
                       'weight': pairs.data, 'weight_all_targets': np.asarray(wa[pairs.row, pairs.col]).ravel(),
                       'reciprocal': np.asarray(b[pairs.row, pairs.col]).ravel() + np.asarray(b[pairs.col, pairs.row]).ravel() == 2})
    ue = ue.sort_values(['source', 'target']).reset_index(drop=True)
    ue.to_parquet(out / 'undirected_edges.parquet', index=False)
    for name, matrix in [('adjacency_binary', b), ('adjacency_weighted_undirected', w), ('adjacency_all_targets_undirected', wa)]:
        sparse.save_npz(out / f'{name}.npz', matrix)
    nc, comp = connected_components(u, directed=False); sizes = np.bincount(comp)
    nodes['component'] = comp; nodes['component_size'] = sizes[comp]
    nodes['degree'] = np.diff(u.indptr); nodes['outdegree'] = np.diff(b.indptr); nodes['indegree'] = np.diff(b.tocsc().indptr)
    nodes['weighted_strength'] = np.asarray(w.sum(axis=1)).ravel()
    nodes.to_parquet(out / 'nodes.parquet', index=False)
    checks = {'unique_entities': nodes.entity_id.is_unique, 'unique_directed_pairs': not directed.duplicated(['source','target']).any(),
              'no_entity_self_links': bool(np.all(s != t)), 'source_budget_at_most_one': bool((np.asarray(f.sum(axis=1)).ravel() <= 1+1e-12).all()),
              'cohort_handles_preserved_in_alias_map': set(cohort.handle) <= set(aliases.handle),
              'all_target_weights_no_larger': bool((ue.weight_all_targets <= ue.weight+1e-12).all())}
    assert all(checks.values()), checks
    summary = {'version': 2, 'nodes': len(nodes), 'original_cohort_handles': len(cohort), 'merged_surplus_handles': len(cohort)-len(nodes),
               'entities_with_multiple_cohort_handles': int((nodes.cohort_alias_count > 1).sum()),
               'subscriber_conflict_entities': int(nodes.subscriber_conflict.sum()), 'subscriber_sum': int(nodes.subscribers.sum()),
               'handle_subscriber_sum': int(cohort.subscribers.sum()), 'null_id_entities': int(nodes.chat_id.isna().sum()),
               'identity_policy': 'Snapshot chat_id, with handle fallback only for null ID; historical reassignment unresolved.',
               'subscriber_policy': 'One cohort row: newest http_validated_at, then last_crawled_at, then handle; preserve min/max conflicts. No verified count timestamp.',
               'directed_edges': len(directed), 'undirected_edges': len(ue), 'reciprocal_pairs': int(ue.reciprocal.sum()),
               'full_valid_handle_directions_removed_as_entity_loops': loops_removed,
               'components': int(nc), 'giant_component': int(sizes.argmax()), 'giant_nodes': int(sizes.max()), 'isolates': int((nodes.degree == 0).sum()),
               'zero_subscribers': int(nodes.subscribers.eq(0).sum()), 'missing_subscribers': int(nodes.subscribers.isna().sum()),
               'max_subscribers': int(nodes.subscribers.max()), 'max_global_outdegree': int(d.max()),
               'weights': 'Union distinct eligible source/target entities before denominator or induced restriction; q=1/full eligible entity outdegree; w=q+reverse. All-target sensitivity includes invalid destinations from the same eligible source handles, resolving known target IDs.',
               'weight_sensitivity': {'spearman': float(spearmanr(ue.weight, ue.weight_all_targets).statistic),
                                      'sources_valid_positive': int((d>0).sum()), 'sources_denominator_more_than_halved': int(((ad>2*d)&(d>0)).sum()),
                                      'max_denominator_ratio': float(np.max(ad[d>0]/d[d>0]))},
               'sources_sha256': {'graph/crawled_nodes.parquet': sha(out/'crawled_nodes.parquet'),
                                  '../channel_graph_2026-09-30/graph/nodes_indexed.parquet': sha(raw/'nodes_indexed.parquet'),
                                  '../channel_graph_2026-09-30/graph/edges.parquet': sha(raw/'edges.parquet'),
                                  '../channel_graph_filtered_2026-09-30/graph/edges.parquet': sha(valid/'edges.parquet')},
               'cohort_sha256': sha(out/'nodes.parquet'), 'checks': {k: bool(v) for k,v in checks.items()}}
    (a.root/'graph_manifest.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
