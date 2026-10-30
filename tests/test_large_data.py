from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from harness.large_data import aggregate_files, profile_file


class LargeDataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def csv(self, name, rows, fields=('id', 'region', 'amount')):
        path = self.root / name
        with path.open('w', encoding='utf-8', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(fields)
            writer.writerows(rows)
        return path

    def test_exact_decimal_cross_file_first_valid_id_and_count_reconciliation(self):
        first = self.csv('a.csv', [
            ['a', 'East', 'bad'], ['a', 'East', '0.10'],
            ['b', 'East', '0.20'], ['c', 'West', '0'],
            ['n', 'West', 'NaN'], ['m', '', '2'],
            ['ｄ', 'West', '-2.50'], ['z', 'West', 'Infinity'],
        ])
        second = self.csv('b.csv', [[' a ', 'West', '999'], ['d', 'West', '99'], ['e', 'East', '1e40']])
        result = aggregate_files([first, second], group_by=['region'], value='amount', id_column='id')
        self.assertEqual((result['rows_seen'], result['valid'], result['excluded']), (11, 5, 6))
        self.assertEqual(result['exclusion_reasons'], {'duplicate_id': 2, 'invalid_number': 3, 'missing_value': 1})
        self.assertEqual(Decimal(result['totals']['sum']), Decimal('9999999999999999999999999999999999999997.80'))
        self.assertEqual(result['totals']['min'], '-2.50')
        self.assertEqual(result['totals']['count'], 5)
        self.assertTrue(result['spill']['disk_backed'])
        self.assertTrue(result['spill']['temporary_database_removed'])
        self.assertFalse(list(self.root.glob('harness-aggregate-*')))
        self.assertEqual(result['exclusion_examples'][0]['record'], 1)
        self.assertEqual(result['exclusion_examples'][0]['source_path'], str(first.resolve()))

    def test_jsonl_invalid_rows_and_output_groups_are_bounded(self):
        path = self.root / 'rows.jsonl'
        path.write_text('{"id":"a","region":"x","amount":0.1}\nno\n[]\n{"id":"b","region":"y","amount":0.2}\n{"id":"c","region":"z","amount":0}\n', encoding='utf-8')
        result = aggregate_files([path], group_by=['region'], value='amount', max_groups=1, work_dir=self.root)
        self.assertEqual(result['valid'], 3)
        self.assertEqual(result['exclusion_reasons'], {'malformed_json': 1, 'non_object_json': 1})
        self.assertEqual(result['totals']['sum'], '0.3')
        self.assertEqual(len(result['groups']), 1)
        self.assertEqual(result['groups_total'], 3)
        self.assertTrue(result['groups_truncated'])
        self.assertFalse(list(self.root.glob('harness-aggregate-*')))

    def test_profile_is_sample_scoped_bounded_and_hash_is_full_file(self):
        path = self.csv('source.csv', [['a', 'East', '1'], ['b', '', '2.5'], ['c', 'West', 'NaN']])
        result = profile_file(path, sample_rows=2)
        self.assertEqual(result['sampled_rows'], 2)
        self.assertEqual(result['counts_scope'], 'sample')
        self.assertEqual(next(item for item in result['schema'] if item['name'] == 'region')['missing'], 1)
        self.assertEqual(next(item for item in result['schema'] if item['name'] == 'amount')['types'], ['decimal', 'integer'])
        from hashlib import sha256
        self.assertEqual(result['sha256'], sha256(path.read_bytes()).hexdigest())
        self.assertEqual(len(result['sample']), 2)
        self.assertEqual(profile_file(path, sample_rows=0)['sampled_rows'], 0)

    def test_explicit_encoding_and_bom(self):
        path = self.root / 'legacy.csv'
        path.write_text('id,region,amount\na,서울,1\n', encoding='utf-16')
        self.assertEqual(profile_file(path)['encoding'], 'utf-16')
        self.assertEqual(aggregate_files([path], group_by=['region'], value='amount')['groups'][0]['key'], {'region': '서울'})

    def test_filters_dates_and_unit_scales_precede_dedup(self):
        path = self.csv('dates.csv', [
            ['a', ' East ', '100', '31/01/2026'],
            ['a', 'East', '200', '01/02/2026'],
            ['b', 'East', '300', '2026-02-01'],
            ['c', 'West', '0', '01/02/2026'],
        ], ('id', 'region', 'amount', 'day'))
        result = aggregate_files([path], group_by=['day'], value='amount', id_column='id',
                                 date_columns={'day': '%d/%m/%Y'},
                                 units={'amount': {'scale': '0.01', 'unit': 'USD'}},
                                 where={'day': '2026-02-01', 'amount': {'gte': 0}})
        self.assertEqual(result['valid'], 2)
        self.assertEqual(result['totals']['sum'], '2.00')
        self.assertEqual(result['exclusion_reasons'], {'filtered': 1, 'invalid_date': 1})
        self.assertEqual(result['groups'][0]['key'], {'day': '2026-02-01'})

    def test_join_many_to_one_and_missing_matches(self):
        facts = self.csv('facts.csv', [['a', 'x', '1', 'd'], ['b', 'y', '2', 'none'], ['c', 'z', '3', 'd']], ('id', 'region', 'amount', 'dim_id'))
        dimension = self.csv('dim.csv', [['d', 'category']], ('dim_id', 'category'))
        join = {'path': str(dimension), 'left_key': 'dim_id', 'right_key': 'dim_id', 'columns': ['category']}
        result = aggregate_files([facts], group_by=['region'], value='amount', join=join)
        self.assertEqual(result['valid'], 3)
        self.assertEqual(result['join']['matched'], 2)
        self.assertEqual(result['join']['missing_matches'], 1)
        self.assertEqual(result['totals']['sum'], '6')
        self.assertEqual([item['role'] for item in result['sources']], ['fact', 'dimension'])
        result = aggregate_files([facts], group_by=['category'], value='amount', join={**join, 'how': 'inner'})
        self.assertEqual(result['valid'], 2)
        self.assertEqual(result['exclusion_reasons'], {'join_missing': 1})
        self.assertEqual(result['totals']['sum'], '4')

    def test_duplicate_dimension_keys_and_collisions_are_rejected(self):
        facts = self.csv('facts.csv', [['a', 'x', '1', 'd']], ('id', 'region', 'amount', 'dim_id'))
        dimension = self.csv('dim.csv', [['d', 'A'], ['ｄ', 'B']], ('dim_id', 'category'))
        join = {'path': str(dimension), 'left_key': 'dim_id', 'right_key': 'dim_id', 'columns': ['category']}
        with self.assertRaisesRegex(ValueError, 'duplicate dimension key'):
            aggregate_files([facts], group_by=['category'], value='amount', join=join)
        dimension = self.csv('dim.csv', [['d', 'replaced']], ('dim_id', 'region'))
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            aggregate_files([facts], group_by=['region'], value='amount', join={**join, 'columns': ['region']})

    def test_empty_aggregate_and_configuration_errors(self):
        path = self.csv('empty.csv', [])
        result = aggregate_files([path], group_by=[], value='amount')
        self.assertEqual(result['totals'], {'count': 0, 'sum': '0', 'min': None, 'max': None, 'mean': None,
                                           'mean_fraction': {'numerator': '0', 'denominator': 0}, 'mean_precision': 50})
        self.assertEqual(result['groups'], [])
        with self.assertRaisesRegex(ValueError, 'unsupported filter'):
            aggregate_files([path], group_by=[], value='amount', where={'amount': {'sql': 'x'}})
        with self.assertRaisesRegex(ValueError, 'nonnegative'):
            aggregate_files([path], group_by=[], value='amount', max_groups=-1)
        with mock.patch('harness.large_data.shutil.disk_usage', return_value=type('Usage', (), {'free': 100})()):
            with self.assertRaisesRegex(ValueError, 'insufficient free disk'):
                aggregate_files([path], group_by=[], value='amount')

    def test_decimal_mean_has_exact_fraction_and_stream_processes_many_groups(self):
        path = self.root / 'many.csv'
        with path.open('w', encoding='utf-8') as output:
            output.write('id,region,amount\n')
            for i in range(5000):
                output.write(f'{i},{i},{1 if i == 0 else 0}\n')
        result = aggregate_files([path], group_by=['region'], value='amount', id_column='id', max_groups=2)
        self.assertEqual(result['groups_total'], 5000)
        self.assertEqual(result['totals']['mean_fraction'], {'numerator': '1', 'denominator': 5000})
        self.assertEqual(result['totals']['mean'], '0.0002')
        self.assertLess(len(json.dumps(result)), 10000)

    def test_oversized_jsonl_record_excluded_once_and_unit_mismatch(self):
        path=self.root/'large.jsonl'
        path.write_text('{"payload":"'+'x'*(2*1024*1024)+'"}\n{"id":"a","region":"x","amount":1,"currency":"USD"}\n{"id":"b","region":"x","amount":3,"currency":"KRW"}\n')
        result=aggregate_files([path],group_by=['region'],value='amount',units={'amount':{'scale':1,'unit':'USD','unit_column':'currency'}})
        self.assertEqual(result['rows_seen'],3)
        self.assertEqual(result['exclusion_reasons'],{'record_too_large':1,'unit_mismatch':1})
        self.assertEqual(result['totals']['sum'],'1')


if __name__ == '__main__':
    unittest.main()
