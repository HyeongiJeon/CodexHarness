"""Reproducible synthetic intelligence benchmarks; large inputs stay ignored."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

from .sources import resources


def timed(function, *args, **kwargs):
    start = time.perf_counter(); result = function(*args, **kwargs)
    return result, round(time.perf_counter() - start, 6)


def make_data(root: Path, count: int) -> tuple[list[Path], dict, dict]:
    root.mkdir(parents=True, exist_ok=True)
    paths = [root/'part1.csv', root/'part2.csv']
    expected, reasons, valid = Counter(), Counter(), 0
    handles = [p.open('w') for p in paths]
    try:
        for f in handles: f.write('id,region,amount,dim_id\n')
        for i in range(count):
            missing, bad = i % 101 == 0, i % 103 == 0
            duplicate = i > 0 and i % 109 == 0
            identity = i - 1 if duplicate else i
            region = '' if missing else f'R{i%4}'
            amount = 'NaN' if bad else f'{i%100//100}.{i%100:02d}'
            handles[int(i >= count//2)].write(f'{identity},{region},{amount},{i%10}\n')
            if missing: reasons['missing_value'] += 1
            elif bad: reasons['invalid_number'] += 1
            elif duplicate and (i-1) % 101 and (i-1) % 103: reasons['duplicate_id'] += 1
            else:
                expected[f'C{i%5}'] += i % 100; valid += 1
    finally:
        for f in handles: f.close()
    dimension = root/'dimensions.csv'
    dimension.write_text('dim_id,category\n'+''.join(f'{i},C{i%5}\n' for i in range(10)))
    config = {'group_by':['category'], 'value':'amount', 'id_column':'id', 'required':['region'],
              'join':{'path':str(dimension.resolve()), 'left_key':'dim_id', 'right_key':'dim_id','columns':['category'],'how':'inner'}}
    truth = {'valid':valid, 'excluded':count-valid, 'exclusion_reasons':dict(reasons),
             'group_cents':dict(expected), 'sum_cents':sum(expected.values())}
    return paths, config, truth


def worker(job: dict) -> dict:
    from .large_data import aggregate_files
    if job['kind'] == 'aggregate':
        result, elapsed = timed(aggregate_files, job['paths'], **job['config'])
        truth = job['truth']
        checks = {'valid_count':result['valid']==truth['valid'], 'excluded_count':result['excluded']==truth['excluded'],
                  'reasons':result['exclusion_reasons']==truth['exclusion_reasons'],
                  'sum':Decimal(result['totals']['sum'])==Decimal(truth['sum_cents'])/100,
                  'groups':all(Decimal(g['sum'])==Decimal(truth['group_cents'][g['key']['category']])/100 for g in result['groups']),
                  'join_no_multiplication':result['join']['matched']==result['rows_seen']}
        summary = {key:result[key] for key in ('rows_seen','valid','excluded','exclusion_reasons','totals','groups','spill')}
    else:
        from .data import clean_sales_csv, aggregate_by_region
        path = Path(job['paths'][0])
        if job['kind'] == 'legacy':
            start = time.perf_counter(); cleaned = clean_sales_csv(path.read_text()); groups = aggregate_by_region(cleaned.rows)
            elapsed = round(time.perf_counter()-start,6)
            summary = {'valid':len(cleaned.rows),'sum':str(sum(Decimal(g['revenue']) for g in groups))}
        else:
            result,elapsed = timed(aggregate_files,[path],group_by=['region'],value='revenue',id_column='transaction_id')
            summary = {'valid':result['valid'],'sum':result['totals']['sum']}
        checks = {'valid_count':summary['valid']==job['count'], 'sum':Decimal(summary['sum'])==Decimal(job['count'])/10}
    return {'kind':job['kind'], 'elapsed_seconds':elapsed, 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'checks':checks, 'passed':all(checks.values()), 'result':summary}


def process_job(root: Path, job: dict) -> dict:
    path=root/'job.json';path.write_text(json.dumps(job))
    completed=subprocess.run([sys.executable,'-m','harness.intelligence_benchmark','--worker',str(path)],capture_output=True,text=True,timeout=600)
    if completed.returncode:
        raise ValueError(f'benchmark worker failed: {completed.stderr[-2000:]}')
    return json.loads(completed.stdout)


def make_corpus(root: Path, count: int = 120) -> dict:
    root.mkdir(parents=True,exist_ok=True)
    padding='unrelated maintenance schedule and logistics 기록\n'*100
    facts = [
        ('001_base.md', 'BASE-42',100,'approved','2026-01-01','2026-06-01',''),
        ('002_change.md','CHANGE-42',110,'approved','2026-06-01',None,''),
        ('003_exception.md','EXCEPTION-42',120,'approved','2026-06-01',None,'urgent approved'),
        ('004_latest_draft.md','DRAFT-42',999,'draft','2026-11-01',None,''),
        ('005_record.md','RECORD-42',115,'approved','2026-10-01',None,'observed record'),
    ]
    for i,(name,tag,value,status,start,end,condition) in enumerate(facts):
        header=f'document_date: 2026-10-{i+1:02d}\nversion: {99 if status=="draft" else i+1}\nstatus: {status}\neffective_from: {start}\nentity: LOT-42\n'
        if end:header+=f'effective_to: {end}\n'
        fact={'entity':'LOT-42','attribute':'actual_mass' if tag=='RECORD-42' else 'limit','value':value,'unit':'kg','condition':condition,'tag':tag}
        if tag=='EXCEPTION-42':fact['exception_to']='limit'
        line='FACT '+json.dumps(fact,ensure_ascii=False)+'\n'
        # Relevant evidence at the front, middle and very last line.
        body=line+padding if i==0 else padding+line+padding if i==1 else padding*2+line
        (root/name).write_text(header+body)
    for i,value in enumerate((10,11)):
        (root/f'conflict_{i}.md').write_text('document_date: 2026-10-01\nstatus: approved\neffective_from: 2026-01-01\nFACT '+json.dumps({'entity':'LOT-X','attribute':'quota','value':value,'unit':'kg','tag':'CONFLICT-77'})+'\n')
    for i in range(count-7):(root/f'noise_{i:03d}.md').write_text(f'version: 99\nstatus: draft\n# Distractor {i}\n'+padding*2+f'Not the target: LOT-420, BASE-420. Count {100+i}\n')
    return {'tags':[f[1] for f in facts], 'expected_files':count}


def corpus_job(root: Path) -> dict:
    from .corpus import inventory,index_corpus,search
    from .evidence import evidence_pack,serialized,verify,synthesize
    source=root/'sources'; truth=make_corpus(source);db=root/'corpus.db'
    files,invtime=timed(lambda:list(inventory(source)))
    report,idxtime=timed(index_corpus,source,db)
    found,querytime=timed(lambda:[search(db,q,mode='identifier') for q in truth['tags']])
    literal_pack=evidence_pack(db,truth['tags'],max_evidence=8,max_chars=10000)
    pack,packtime=timed(evidence_pack,db,truth['tags'],max_evidence=8,max_chars=10000,mode='identifier')
    audit,audittime=timed(verify,pack)
    answer,syntime=timed(synthesize,pack,entity='LOT-42',as_of='2026-10-30',attribute='limit')
    conflict=synthesize(evidence_pack(db,['CONFLICT-77']),entity='LOT-X',as_of='2026-10-30')
    missing=synthesize(evidence_pack(db,['NO-SUCH-CLAIM']),entity='MISSING',as_of='2026-10-30')
    core_recall=sum(any(tag in e['excerpt'] for e in pack['evidence']) for tag in truth['tags'])/len(truth['tags'])
    (root/'pack.json').write_text(serialized(pack));(root/'answer.json').write_text(json.dumps(answer,ensure_ascii=False,indent=2))
    checks={'file_count':len(files)==truth['expected_files'],'all_searches_hit':all(x['result_count'] for x in found),
            'core_evidence_recall':core_recall==1,'source_verification':audit['status']=='verified',
            'correct_effective_and_exception':answer['status']=='supported' and {(str(a['value']),a['condition']) for a in answer['answer']}=={('110',''),('120','urgent approved')},
            'draft_excluded':all(str(a['value'])!='999' for a in answer.get('answer') or []),
            'conflict_detected':conflict['status']=='conflict','missing_blocks_answer':missing['answer'] is None,
            'context_budget':len(serialized(pack))<=10000}
    return {'inventory_seconds':invtime,'index_seconds':idxtime,'search_five_queries_seconds':querytime,
            'pack_seconds':packtime,'verify_seconds':audittime,'synthesis_seconds':syntime,
            'files':len(files),'segments':report['segment_count'],'corpus_bytes':sum(f['size_bytes'] for f in files),
            'pack_chars':len(serialized(pack)),'pack_utf8_bytes':len(serialized(pack).encode()),
            'core_evidence_recall':core_recall,'evidence_precision':sum('FACT ' in e['excerpt'] for e in pack['evidence'])/max(len(pack['evidence']),1),
            'literal_pack_evidence_precision':sum('FACT ' in e['excerpt'] for e in literal_pack['evidence'])/max(len(literal_pack['evidence']),1),
            'quote_verification_rate':audit['verified']/max(audit['total'],1),
            'checks':checks,'passed':all(checks.values()),'fts_available':report['fts_available']}


def run(output: Path, row_counts=(100000,1000000)) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    results={'resources':resources(output),'structured':[],'model_calls':0,'model_tokens':0,
             'memory_metric':'Linux isolated Python process peak ru_maxrss KiB; includes interpreter, not a hard cap'}
    for count in row_counts:
        target=output/f'rows-{count}';paths,config,truth=make_data(target,count)
        result=process_job(target,{'kind':'aggregate','paths':[str(p.resolve()) for p in paths],'config':config,'truth':truth})
        results['structured'].append(result)
    baseline=output/'baseline';baseline.mkdir(exist_ok=True)
    sales=baseline/'sales.csv';count=min(row_counts[0],100000)
    with sales.open('w') as f:
        f.write('transaction_id,date,region,units,revenue\n')
        for i in range(count):f.write(f'{i},2026-01-01,R{i%4},1,0.10\n')
    results['baseline']=[process_job(baseline,{'kind':kind,'paths':[str(sales.resolve())],'count':count}) for kind in ('legacy','streaming')]
    results['corpus']=corpus_job(output/'documents')
    results['passed']=all(r['passed'] for r in results['structured']+results['baseline']) and results['corpus']['passed']
    (output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    return results


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path,required=True)
    print(json.dumps(worker(json.loads(parser.parse_args().worker.read_text()))))
