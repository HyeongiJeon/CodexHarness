import json
from pathlib import Path
import tempfile
import unittest

from harness.corpus import index_corpus, search
from harness.evidence import evidence_pack
from harness.prose_evaluation import prepare, score


class ProseScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);fixture=root/'fixture';(fixture/'corpus').mkdir(parents=True)
        (fixture/'corpus'/'sub').mkdir();(fixture/'corpus'/'sub'/'n.md').write_text('보조 자료\n')
        (fixture/'corpus'/'policy.md').write_text('status: approved\n승인된 시험 기준은 100kg이다.\n')
        (fixture/'questions.json').write_text('{"questions":[{"id":"Q1","question":"기준은?"}]}')
        (fixture/'oracle.json').write_text('private oracle must never be copied')
        self.work=root/'run';prepare(self.work,fixture)
        self.db=self.work/'index.db';index_corpus(self.work/'inputs/corpus',self.db)
        self.pack=evidence_pack(self.db,['기준'])
        (self.work/'packs/Q1.json').write_text(json.dumps(self.pack))
        self.ledger={'questions':[{'id':'Q1','pack':'packs/Q1.json','searches':[search(self.db,'기준')]}]}
        (self.work/'retrieval.json').write_text(json.dumps(self.ledger))
        self.gold={'questions':[{'id':'Q1','expected_status':'supported','expected_values':{'limit_kg':100},
            'required_evidence':[{'document':'policy.md','contains':'100kg'}]}]}
        self.cite=self.pack['evidence'][0]['citation_id']

    def answers(self,value=100,cite=None):
        return {'answers':[{'question_id':'Q1','status':'supported','values':{'limit_kg':value},'citations':[cite or self.cite]}]}

    def test_input_separation_and_wrong_certainty_not_hidden_by_valid_quotes(self):
        self.assertFalse((self.work/'inputs/oracle.json').exists())
        result=score(self.work,self.gold,self.answers(120))
        self.assertEqual(result['metrics']['false_definitive_conclusions'],1)
        self.assertEqual(result['metrics']['synthesis_failures'],1)
        self.assertEqual(result['metrics']['source_verification_failures'],0)

    def test_failures_are_classified_independently(self):
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['correct_answers'],1)
        bad=score(self.work,self.gold,self.answers(cite='invented'))
        self.assertEqual(bad['metrics']['source_verification_failures'],1)
        self.assertEqual(bad['metrics']['false_definitive_conclusions'],1)
        self.pack['truncated']=True;(self.work/'packs/Q1.json').write_text(json.dumps(self.pack))
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['false_definitive_conclusions'],1)
        self.ledger['questions'][0]['searches']=[];(self.work/'retrieval.json').write_text(json.dumps(self.ledger))
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['retrieval_failures'],1)

    def test_metadata_change_and_truncated_auditor_rejection_are_not_hidden(self):
        self.pack['evidence'][0]['metadata']['status']='draft'
        (self.work/'packs/Q1.json').write_text(json.dumps(self.pack))
        m=score(self.work,self.gold,self.answers())['metrics']
        self.assertEqual((m['source_verification_failures'],m['false_definitive_conclusions']),(1,1))
        self.assertEqual(m['citations_verified'],0)
        self.pack['evidence'][0]['metadata']=None;(self.work/'packs/Q1.json').write_text(json.dumps(self.pack))
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['source_verification_failures'],1)
        self.pack['evidence'][0]['metadata']={'status':'draft'}
        self.pack['evidence'][0]['metadata']['status']='approved';self.pack['truncated']=True
        (self.work/'packs/Q1.json').write_text(json.dumps(self.pack))
        m=score(self.work,self.gold,self.answers(),{'questions':[{'question_id':'Q1','supported_by_sources':False}]})['metrics']
        self.assertEqual((m['audit_caught_false_certainties'],m['audit_false_rejections'],m['source_verification_failures']),(1,0,0))

    def test_input_set_changes_invalidate_trial_including_nested_files(self):
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['correct_answers'],1)
        nested=self.work/'inputs/corpus/sub/n.md';top=self.work/'inputs/corpus/policy.md';original=top.read_text()
        for change in (lambda:nested.write_text('x'),lambda:top.write_text('y'),
                       lambda:(self.work/'inputs/corpus/sub/new.md').write_text('z'),lambda:nested.unlink()):
            change()
            with self.assertRaises(ValueError):score(self.work,self.gold,self.answers())
            nested.parent.mkdir(exist_ok=True);nested.write_text('보조 자료\n');top.write_text(original)
            (self.work/'inputs/corpus/sub/new.md').unlink(missing_ok=True)
        self.assertEqual(score(self.work,self.gold,self.answers())['metrics']['correct_answers'],1)
