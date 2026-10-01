"""Exclude explicitly invalid endpoints; retain unknown and deferred states.

Build a dated derivative, never overwrite the original observed graph. Raw
per-exposure validation flags are not eligibility gates. The invalid-channel
registry and registry invalidation/current type flags determine exclusions.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.sparse import load_npz, save_npz
from scipy.sparse.csgraph import connected_components


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--audit',type=Path,required=True)
    args=parser.parse_args()
    out=args.output
    graph=out/'graph'
    graph.mkdir(parents=True,exist_ok=True)
    if (graph/'adjacency_binary.npz').exists():
        raise FileExistsError('Use a new dated output directory')
    nodes=pd.read_parquet(args.source/'graph/nodes_indexed.parquet').sort_values('node_id')
    a=load_npz(args.source/'graph/adjacency_binary.npz')
    assert np.array_equal(nodes.node_id,np.arange(len(nodes)))
    reason=nodes.recorded_registry_reasons
    bad_reason=reason.notna() & ~reason.eq('deferred_giant_channel')
    bad=nodes.registry_invalidated_at.notna()|nodes.registry_is_channel.eq(False)|bad_reason
    keep=~bad.to_numpy()
    b=a[keep][:,keep].tocsr()
    u=b.maximum(b.T)
    nc,component=connected_components(u,directed=False)
    raw_out=np.diff(a.indptr)
    retained_targets=np.asarray(a[:,keep].sum(axis=1)).ravel().astype(int)
    retained_out=retained_targets.copy();retained_out[~keep]=0
    audit=nodes[['handle','registry_is_channel','registry_invalidated_at','recorded_registry_reasons']].copy()
    audit['original_outdegree']=raw_out
    audit['excluded_target_count']=raw_out-retained_targets
    audit['retained_outdegree']=retained_out
    audit['source_excluded']=bad.to_numpy()
    audit.sort_values(['original_outdegree','handle'],ascending=[False,True]).to_parquet(out/'outgoing_source_audit.parquet',index=False)
    audit.nlargest(50,'original_outdegree').to_json(out/'top_outgoing_sources.json',orient='records',indent=2,date_format='iso')
    audit.loc[bad].to_parquet(out/'excluded_nodes.parquet',index=False)
    nn=nodes.loc[keep].copy().rename(columns={'node_id':'original_node_id'})
    nn.insert(0,'node_id',np.arange(len(nn)))
    nn['observed_outdegree']=np.diff(b.indptr)
    nn['observed_indegree']=np.diff(b.tocsc().indptr)
    nn['outgoing_links_observed']=nn.observed_outdegree>0
    nn.to_parquet(graph/'nodes_indexed.parquet',index=False,compression='zstd')
    save_npz(graph/'adjacency_binary.npz',b)
    table=pq.read_table(args.source/'graph/edges.parquet')
    handles=pd.Index(nodes.handle)
    src=handles.get_indexer(table.column('source_handle').to_pandas())
    dst=handles.get_indexer(table.column('target_handle').to_pandas())
    assert (src>=0).all() and (dst>=0).all()
    mask=keep[src]&keep[dst]
    assert int(mask.sum())==b.nnz
    pq.write_table(table.filter(mask),graph/'edges.parquet',compression='zstd')
    totals={'original_nodes':len(nodes),'original_directed_edges':int(a.nnz),
        'original_undirected_edges':int(a.maximum(a.T).nnz//2),
        'excluded_nodes':int(bad.sum()),'retained_nodes_including_isolates':len(nn),
        'retained_directed_edges':int(b.nnz),'retained_undirected_edges':int(u.nnz//2),
        'removed_directed_edges':int(a.nnz-b.nnz),
        'edges_from_invalid_sources':int(a[~keep].nnz),
        'edges_to_invalid_targets':int(a[:,~keep].nnz),
        'components':int(nc),'giant_nodes':int(np.bincount(component).max()),
        'isolates':int((np.diff(u.indptr)==0).sum()),
        'degree_one_nodes':int((np.diff(u.indptr)==1).sum()),
        'deferred_nodes_retained':int(nn.recorded_registry_reasons.eq('deferred_giant_channel').sum()),
        'retained_nodes_with_unknown_registry_type':int(nn.registry_is_channel.isna().sum())}
    policy={'created_at':datetime.now(timezone.utc).isoformat(),'input_root':str(args.source.resolve()),
        'audit_root':str(args.audit.resolve()),'display_note':'Known-invalid nodes excluded; unknown status retained',
        'exclude':'Registry invalidated_at is nonnull OR registry is_channel is false OR an invalid_channels reason other than deferred_giant_channel is recorded',
        'missing_validation':'Retained; no positive exposure-validation requirement',
        'degree_threshold':None,'temporary_deferrals':'Retained unless independently invalidated',
        'isolates':'All eligible original nodes retained, including nodes isolated by edge removal',
        'snapshot_versions':json.loads((args.source/'snapshot_versions.json').read_text()),
        'totals':totals}
    # Reconcile against an independent database aggregation, not just this filter.
    record=json.loads((args.audit/'results/filtered_graph_totals.json').read_text())
    assert record['status']['state']=='SUCCEEDED' and not record.get('error')
    remote={k:int(v) for k,v in record['rows'][0].items()}
    for k,v in remote.items():assert totals[k]==v,(k,totals[k],v)
    top_remote=json.loads((args.audit/'results/largest_outgoing_source_audit.json').read_text())['rows']
    indexed=audit.set_index('handle')
    for r in top_remote:
        for k in ['original_outdegree','retained_outdegree','excluded_target_count','source_excluded']:
            assert int(indexed.loc[r['source_handle'],k])==int(r[k]),(r,k)
    policy['verification']={'all_sql_totals_match':True,'top_50_sources_match_sql':True,
        'all_edge_endpoints_pass_filter':True,'original_graph_preserved':True}
    (out/'graph_filter.json').write_text(json.dumps(policy,indent=2)+'\n')
    (out/'snapshot_versions.json').write_text(json.dumps(policy['snapshot_versions'],indent=2)+'\n')
    print(json.dumps(policy,indent=2))

if __name__=='__main__':main()
