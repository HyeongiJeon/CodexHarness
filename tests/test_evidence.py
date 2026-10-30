import copy
import json
from pathlib import Path
import tempfile
import unittest

from harness.corpus import index_corpus
from harness.evidence import evidence_pack, serialized, synthesize, verify, compare_calculation


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.docs=self.root/'docs';self.docs.mkdir();self.db=self.root/'index.db'

    def doc(self,name,value,status='approved',start='2026-01-01',condition='',end=None):
        content=f'document_date: 2026-10-01\nversion: 2\nstatus: {status}\neffective_from: {start}\nentity: LINE-7\n'
        if end:content+=f'effective_to: {end}\n'
        content+='FACT '+json.dumps({'entity':'LINE-7','attribute':'limit','value':value,'unit':'kg','condition':condition},ensure_ascii=False)+'\n'
        (self.docs/name).write_text(content)

    def pack(self,**kwargs):
        index_corpus(self.docs,self.db)
        return evidence_pack(self.db,['FACT'],max_chars=16000,**kwargs)

    def test_effective_not_latest_draft_and_conditional_exception(self):
        self.doc('base.md','100',end='2026-06-01')
        self.doc('change.md','110',start='2026-06-01')
        self.doc('exception.md','120',start='2026-06-01',condition='urgent')
        self.doc('latest.md','999',status='draft',start='2026-11-01')
        pack=self.pack();self.assertEqual(verify(pack)['status'],'verified')
        report=synthesize(pack,entity='LINE-7',as_of='2026-10-30')
        self.assertEqual(report['status'],'supported')
        self.assertEqual({(x['value'],x['condition']) for x in report['answer']},{('110',''),('120','urgent')})
        self.assertTrue(all(x['origin']=='source_record' for x in report['facts']))

    def test_conflict_and_missing_evidence_never_emit_answer(self):
        self.doc('a.md','10');self.doc('b.md','11')
        report=synthesize(self.pack(),entity='LINE-7',as_of='2026-10-30')
        self.assertEqual(report['status'],'conflict');self.assertIsNone(report['answer'])
        pack=evidence_pack(self.db,['missing-keyword'])
        self.assertEqual(pack['status'],'insufficient_evidence')
        self.assertIsNone(synthesize(pack,entity='LINE-7',as_of='2026-10-30')['answer'])

    def test_truncated_retrieval_never_confirms_a_retained_value(self):
        from unittest.mock import patch
        from harness.corpus import search
        self.doc('a.md','100');self.doc('b.md','120')
        index_corpus(self.docs,self.db)
        one=evidence_pack(self.db,['FACT'],max_evidence=1)
        char_limited=evidence_pack(self.db,['FACT'],max_chars=len(serialized(one))+150)
        def limited_search(*args,**kwargs):
            kwargs['limit']=1
            return search(*args,**kwargs)
        with patch('harness.evidence.search',side_effect=limited_search):
            search_limited=evidence_pack(self.db,['FACT'],max_evidence=10)
        for label,pack in [('count',one),('chars',char_limited),('search',search_limited)]:
            with self.subTest(limit=label):
                self.assertTrue(pack['truncated'])
                self.assertEqual(pack['uncovered_queries'],[])
                self.assertEqual(verify(pack)['status'],'verified')
                report=synthesize(pack,entity='LINE-7',as_of='2026-10-30')
                self.assertEqual(report['status'],'insufficient_evidence')
                self.assertIsNone(report['answer'])
                self.assertTrue(any(m.get('code')=='retrieval_truncated' for m in report['missing_evidence']))

    def test_retained_conflict_and_independently_complete_scope(self):
        self.doc('a.md','100');self.doc('b.md','120');self.doc('c.md','130')
        pack=self.pack(max_evidence=2)
        self.assertTrue(pack['truncated'])
        self.assertEqual(synthesize(pack,entity='LINE-7',as_of='2026-10-30')['status'],'conflict')
        for name in ('b.md','c.md'):
            p=self.docs/name;p.write_text(p.read_text().replace('LINE-7','OTHER-8'))
        index_corpus(self.docs,self.db)
        pack=evidence_pack(self.db,['FACT'],entity='LINE-7',max_evidence=1)
        self.assertFalse(pack['truncated'])
        report=synthesize(pack,entity='LINE-7',as_of='2026-10-30')
        self.assertEqual(report['status'],'supported')
        self.assertEqual(report['retrieval_scope']['filters']['entity'],'LINE-7')

    def test_tampered_excerpt_location_hash_and_metadata(self):
        self.doc('a.md','10');pack=self.pack()
        self.assertEqual(verify({'evidence':[None]})['status'],'unverified')
        for mutation in ('excerpt','locator','source_path','evidence_id','source_hash'):
            changed=copy.deepcopy(pack)
            changed['evidence'][0][mutation]={'line':99999} if mutation=='locator' else 'fabricated'
            self.assertEqual(verify(changed)['status'],'unverified',mutation)
        changed=copy.deepcopy(pack);changed['evidence'][0]['metadata']['status']='draft'
        self.assertEqual(synthesize(changed,entity='LINE-7',as_of='2026-10-30')['status'],'insufficient_evidence')
        (self.docs/'a.md').write_text('changed')
        self.assertEqual(verify(pack)['status'],'unverified')

    def test_size_count_and_required_query_coverage(self):
        for i in range(12):self.doc(f'{i}.md',str(i))
        index_corpus(self.docs,self.db)
        pack=evidence_pack(self.db,['FACT','absent'],max_evidence=2,max_chars=4000)
        self.assertLessEqual(len(pack['evidence']),2)
        self.assertLessEqual(len(serialized(pack)),4000)
        self.assertEqual(pack['status'],'insufficient_evidence')
        self.assertIn('absent',pack['uncovered_queries'])

    def test_units_and_exact_large_values_do_not_collapse(self):
        self.doc('a.md','10000000000000000000000000001')
        self.doc('b.md','10000000000000000000000000002')
        self.assertEqual(synthesize(self.pack(),entity='LINE-7',as_of='2026-10-30')['status'],'conflict')

    def test_unquoted_decimal_facts_remain_exact(self):
        self.doc('a.md','placeholder');self.doc('b.md','placeholder')
        for name, number in [('a.md','9007199254740992.1'),('b.md','9007199254740992.2')]:
            p=self.docs/name;p.write_text(p.read_text().replace('"placeholder"',number))
        self.assertEqual(synthesize(self.pack(),entity='LINE-7',as_of='2026-10-30')['status'],'conflict')

    def test_two_distant_matches_in_one_segment_retain_both_quotes(self):
        (self.docs/'a.txt').write_text('ALPHA'+'x'*3000+'OMEGA')
        index_corpus(self.docs,self.db)
        pack=evidence_pack(self.db,['ALPHA','OMEGA'],max_chars=12000)
        self.assertEqual(pack['status'],'evidence_found')
        self.assertEqual(len({e['citation_id'] for e in pack['evidence']}),2)
        self.assertTrue(all(any(q in e['excerpt'] for e in pack['evidence']) for q in ('ALPHA','OMEGA')))

    def test_known_partial_extraction_blocks_supported_answer(self):
        self.doc('a.md','10')
        p=self.docs/'a.md';p.write_text(p.read_text()+'padding\n'*200+'FACT {"entity":"LINE-7","attribute":"limit","value":20}\n')
        index_corpus(self.docs,self.db,max_chars=300)
        pack=evidence_pack(self.db,['FACT'])
        self.assertEqual(synthesize(pack,entity='LINE-7',as_of='2026-10-30')['status'],'insufficient_evidence')

    def test_recomputed_multifile_total_compares_to_document_claim(self):
        from harness.large_data import aggregate_files
        self.doc('a.md','0.30');pack=self.pack()
        a=self.root/'a.csv';b=self.root/'b.csv'
        a.write_text('id,amount\na,0.10\n');b.write_text('id,amount\nb,0.20\n')
        config={'group_by':[],'value':'amount','id_column':'id','units':{'amount':{'scale':1,'unit':'kg'}}}
        report=aggregate_files([a,b],**config);report['calculation_contract']={'paths':[str(a),str(b)],'config':config}
        kwargs={'entity':'LINE-7','attribute':'limit','as_of':'2026-10-30','unit':'kg'}
        self.assertEqual(compare_calculation(pack,report,**kwargs)['status'],'verified')
        truncated=copy.deepcopy(pack);truncated['truncated']=True
        self.assertEqual(compare_calculation(truncated,report,**kwargs)['status'],'insufficient_evidence')
        tampered=json.loads(json.dumps(report));tampered['units']['amount']['unit']='USD'
        self.assertEqual(compare_calculation(pack,tampered,**kwargs)['status'],'unverified')
        self.doc('a.md','0.31');pack=self.pack()
        self.assertEqual(compare_calculation(pack,report,**kwargs)['status'],'conflict')
        report['totals']['sum']='999'
        self.assertEqual(compare_calculation(pack,report,**kwargs)['status'],'unverified')
