"""Pack the identity-resolved graph into a portable WebGL2 atlas."""
from pathlib import Path
import argparse,json,base64,gzip,hashlib
import numpy as np
import pandas as pd
from scipy.sparse import load_npz
import sys
sys.path.insert(0,str(Path(__file__).parent/'crawled_graph'))
import community_colors
p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();out=a.root/'visualization';out.mkdir(exist_ok=True)
fingerprint=json.loads((a.root/'layout/cache_fingerprint.json').read_text())
for rel,digest in fingerprint['inputs'].items():
    assert hashlib.sha256((a.root/rel).read_bytes()).hexdigest()==digest, 'Layout is stale: '+rel
n=pd.read_parquet(a.root/'layout/nodes_layout.parquet').sort_values('node_id');e=pd.read_parquet(a.root/'graph/undirected_edges.parquet');b=load_npz(a.root/'graph/adjacency_binary.npz')
cols=['x','y','subscribers','degree','indegree','outdegree','global_valid_outdegree','core','community','community_coarse','community_fine','component','recorded_visits','total_messages_processed']
na=n[cols].to_numpy(dtype='<f4');ea=np.zeros((len(e),4),dtype='<f4');ea[:,:3]=e[['source','target','weight']].to_numpy(dtype='<f4');s=e.source.to_numpy();t=e.target.to_numpy();ea[:,3]=np.asarray(b[s,t]).ravel()+2*np.asarray(b[t,s]).ravel()
assert np.isfinite(na).all() and np.isfinite(ea).all();assert (ea[:,3]>0).all()
manifest=json.loads((a.root/'graph_manifest.json').read_text());lm=json.loads((a.root/'layout/layout_manifest.json').read_text())
overlap=lm.get('overlap_removal')
assert overlap and overlap['remaining_overlaps_including_padding']==0, 'Run remove_crawled_node_overlaps.py before rendering this template'
assert overlap['output_positions_sha256']==hashlib.sha256((a.root/'layout/positions.npy').read_bytes()).hexdigest(), 'Stale overlap geometry'
assert np.array_equal(np.load(a.root/'layout/positions.npy'),n[['x','y']].to_numpy()), 'Layout files disagree'
style_path=out/'style.json'
default={'subscriber_reference':100000,'reference_diameter_css_px':8.,'zero_marker_css_px':2.,'zero_marker_opacity':.25,
         'edge_width_min_css_px':.6,'edge_width_max_css_px':1.3,
         'edge_tone_cap':.45,'edge_color':'#8099b0','background':'#0a121d','monochrome':'#8ccdc4',
         'edge_base_width_css_px':.9,'edge_ink_min_length_world':8.,'edge_calibration_quantiles':[.5,.995],
         'edge_highlight_cap':.45,'edge_highlight_length_exponent':.5,'edge_highlight_calibration_quantiles':[.5,.99],'edge_highlight_color':'#d6e6f5',
         'edge_context_dim_selection':.08,'edge_context_dim_community':.35,
         'continuous_ramp':['#3d7bab','#4dc4b0','#ffc26e'],
         'palette':['#70cbb8','#e9ad69','#87a6ec','#d68abe','#bdcc77','#77c5da','#c49bed','#e98884','#b8ceda','#c99d7a','#a5b9e5','#84b8a0'],
         'log_weight_min':float(np.log(e.weight.quantile(.01))),'log_weight_max':float(np.log(e.weight.quantile(.99)))}
style=json.loads(style_path.read_text()) if style_path.exists() else default
assert set(style)==set(default), 'Unknown or missing style keys; descriptive metadata is stored in render_manifest, not editable style.'
for key,value in style.items():
    if isinstance(default[key],(float,int)): assert isinstance(value,(float,int)) and np.isfinite(value),key
assert style['subscriber_reference']>0 and style['reference_diameter_css_px']>0
assert 0<style['edge_tone_cap']<=1 and 0<style['edge_width_min_css_px']<=style['edge_width_max_css_px']
assert style['log_weight_min']<style['log_weight_max'] and 0< style['zero_marker_css_px'] and 0<=style['zero_marker_opacity']<=1
import re
assert 0<style['edge_highlight_cap']<=1 and 0<=style['edge_highlight_length_exponent']<=1 and style['edge_base_width_css_px']>0 and style['edge_ink_min_length_world']>0
assert 0<style['edge_context_dim_selection']<=1 and 0<style['edge_context_dim_community']<=1
assert all(len(style[k])==2 and 0<style[k][0]<style[k][1]<1 for k in ['edge_calibration_quantiles','edge_highlight_calibration_quantiles'])
assert len(style['edge_calibration_quantiles'])==2 and 0<style['edge_calibration_quantiles'][0]<style['edge_calibration_quantiles'][1]<1
for colors in [style['palette'],style['continuous_ramp'],[style['background'],style['edge_color'],style['monochrome'],style['edge_highlight_color']]]:
    assert colors and all(isinstance(c,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in colors)
assert len(style['continuous_ramp'])==3
style_path.write_text(json.dumps(style,indent=2)+'\n')
al=pd.read_parquet(a.root/'graph/aliases.parquet'); aliaslists=al.groupby('node_id').handle.agg(list)
data={'labels':n.handle.tolist(),'entity_ids':n.entity_id.tolist(),'aliases':[aliaslists.get(i,[]) for i in range(len(n))],
      'subscriber_ranges':n[['subscribers_min','subscribers_max']].to_numpy().tolist(),
      'global_all_outdegree':n.global_all_outdegree.tolist(),'community_all_targets':n.community_all_targets.tolist(),
      'nodes':base64.b64encode(na.tobytes()).decode(),'edges':base64.b64encode(ea.tobytes()).decode(),
      'weights_all_targets':base64.b64encode(e.weight_all_targets.to_numpy(dtype='<f4').tobytes()).decode(),
      'node_columns':cols,'edge_columns':['source','target','fractional_weight','direction_bits'],'graph':manifest,'layout':lm,'style':style,
      'legend_weights':[float(e.weight.quantile(p)) for p in [.01,.5,.99]],'layout_sha256':hashlib.sha256((a.root/'layout/positions.npy').read_bytes()).hexdigest(),'cohort_sha256':manifest['cohort_sha256']}
# Adjacency-aware palette indices for every partition shown in community colour mode.
giant_region=(n.component.to_numpy()==lm['giant_component'])
color_metrics={}
data['community_color_index']={}
# The overview-tier named communities (top 8 by summed subscribers) also prefer
# mutually distinct colours; weight 5 is small relative to spatial adjacency.
_semantic_path=a.root/'labels/community_labels.json'
_top=[c['community'] for c in sorted(json.loads(_semantic_path.read_text())['communities'],key=lambda c:c['rank_subscribers'])[:8]] if _semantic_path.exists() else []
top_pairs={(u,v):5.0 for i,u in enumerate(_top) for v in _top[i+1:]}
for key,column in [('reference','community'),('coarse','community_coarse'),('fine','community_fine'),('all_targets','community_all_targets')]:
    per_node,chosen,neighbours=community_colors.assign_colors(na[:,:2].astype(float),n[column].to_numpy(),n.subscribers.to_numpy().astype(float),style['palette'],region=giant_region,extra_pairs=top_pairs if key=='reference' else None)
    data['community_color_index'][key]=base64.b64encode(per_node.tobytes()).decode()
    previous={c:c%len(style['palette']) for c in chosen}
    if key=='reference':color_metrics['top8_distinct_colours']=len({chosen[c] for c in _top})
    color_metrics[key]={'modulo_assignment':community_colors.adjacency_similarity(previous,neighbours,style['palette']),'adjacency_assignment':community_colors.adjacency_similarity(chosen,neighbours,style['palette'])}
semantic_path=a.root/'labels/community_labels.json'
if semantic_path.exists():
    semantic=json.loads(semantic_path.read_text())
    partition_hash=hashlib.sha256(n[['entity_id','community']].to_csv(index=False).encode()).hexdigest()
    assert semantic['partition_sha256']==partition_hash, 'Semantic labels refer to a different partition'
    seen=set()
    for item in semantic['communities']:
        cid=item['community']; assert cid not in seen; seen.add(cid)
        members=n[n.community==cid]
        assert len(members)==item['nodes']
        assert hashlib.sha256('\n'.join(sorted(members.entity_id)).encode()).hexdigest()==item['membership_sha256']
        # Reference member near the unweighted spatial median (a weak tie-break for
        # name placement; the browser anchors names to displayed boundary members).
        center=members[['x','y']].median().to_numpy()
        anchor=members.iloc[np.argmin(np.sum((members[['x','y']].to_numpy()-center)**2,axis=1))]
        item['anchor_node']=int(anchor.node_id)

    data['semantic_labels']=semantic
    data['dense_block_community_counts']=[{'community':int(c),'nodes':int(count)} for c,count in n[n.dense_block].groupby('community').size().sort_values(ascending=False).items()]
else:
    data['semantic_labels']={'communities':[]}
    data['dense_block_community_counts']=[]
label_display=out/'label_display.json'
data['label_display']=json.loads(label_display.read_text()) if label_display.exists() else {'version':1,'font_css_px':11,'overview_count':8,'mobile_overview_count':3,'priority':'full_community_subscriber_sum','map_names':{}}
assert data['label_display']['priority']=='full_community_subscriber_sum'
assert data['label_display']['font_css_px']==11
data['label_display'].setdefault('hull_gap_css_px',6)
data['label_display'].setdefault('accept_cost',260)
assert data['label_display']['accept_cost']>0
packed=base64.b64encode(gzip.compress(json.dumps(data,separators=(',',':'),ensure_ascii=True).encode(),compresslevel=6,mtime=0)).decode()
template=Path(__file__).parent/'crawled_graph/atlas.html';html=template.read_text().replace('__PACKED_DATA__',packed).replace('__COMMUNITY_LABEL_SCRIPT__',(template.parent/'community_labels.js').read_text())
(out/'crawled_channels_atlas.html').write_text(html)
report={'nodes':len(n),'edges':len(e),'html_bytes':len(html.encode()),'node_array_columns':cols,
        'all_nodes_have_saved_positions':bool(np.isfinite(na[:,:2]).all()),'all_edges_included':len(ea)==len(e),
        'positive_counts_preserved_exactly_in_float32':bool(np.array_equal(na[:,2].astype('int64'),n.subscribers.to_numpy())),
        'no_individual_subscriber_size_clipping':True,'common_scale_overlap_protection':True,'offline_dependencies':True,'template_sha256':hashlib.sha256(template.read_bytes()).hexdigest(),
        'layout_nodes_sha256':hashlib.sha256((a.root/'layout/nodes_layout.parquet').read_bytes()).hexdigest(),
        'positions_sha256':hashlib.sha256((a.root/'layout/positions.npy').read_bytes()).hexdigest(),
        'semantic_labels':len(data['semantic_labels']['communities']),
        'semantic_labels_sha256':hashlib.sha256(semantic_path.read_bytes()).hexdigest() if semantic_path.exists() else None,
        'community_label_script_sha256':hashlib.sha256((template.parent/'community_labels.js').read_bytes()).hexdigest(),
        'label_display_sha256':hashlib.sha256(label_display.read_bytes()).hexdigest() if label_display.exists() else None,
        'community_color_assignment':color_metrics,
        'weight_float32_max_relative_error':float(np.max(np.abs(ea[:,2]/e.weight.to_numpy()-1))),
        'encoding':{'positive_diameter':'sqrt(subscribers/subscriber_reference) times a common factor: min(requested diameter, overlap-safe world diameter projected to pixels) when protection is enabled',
                    'node_coverage':'Analytic circle/pixel intersection; fractional pixel coverage carries subpixel area. Final 8-bit display quantization remains.',
                    'edges':'Two RGBA32F channels. Base: each tie deposits weight / max(world length, min length) per unit length (ink proportional to weight, zoom-invariant); alpha = cap*log1p(D/d0)/log1p(d1/d0), d0/d1 calibrated once per viewport at the default overview (fixed during pan/zoom/filter/highlight). Highlight (selected channel, or the external ties of a chosen community, optionally one partner): weight / length^highlight_length_exponent; alpha = highlight_cap*log1p(D/h0)/log1p(h1/h0), h0/h1 calibrated once per selection at the overview camera; composited above the base in a brighter colour while other ties dim. Nodes composited after ties.',
                    'core_controls':'Log color scale and slider over attained core values; exact integer entry available.',
                    'zero_counts':'Hidden by default; optional dim 2px non-area diamonds.',
                     'community_colors':'Palette index per partition chosen so spatially adjacent communities (k-nearest marks plus nearby salient marks) receive dissimilar CIELAB colours; categorical identifiers only.',
                     'community_names':'Member-anchored: the near text edge sits a fixed CSS-pixel gap beyond one displayed boundary member glyph; candidates scored over their active zoom range for foreign and own marks under or near the text, neighbourhood dominance, hull-border distance and label collisions.',
                    'layers':['tie_ink_base','tie_highlight','tie_tone_mapping','node_coverage','labels']}}
assert report['positive_counts_preserved_exactly_in_float32']
(out/'render_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
