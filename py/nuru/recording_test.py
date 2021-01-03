import json
import os
import tempfile
import unittest
from unittest import mock

from . import recording


class TestRecording(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    @mock.patch('time.time')
    def test_write(self, time_mock):
        basepath = os.path.join(self.test_dir, 'test_write')
        rec = recording.Recording(basepath)
        transients = (
            'action',
            'midi',
        )

        time_mock.return_value = 0.
        rec.write(dict(
            numbers=[1, 2, 3],
            name='test',
            value=0.,
            t=1234,
        ), transients)

        # empty -> dropped
        time_mock.return_value = 1.
        rec.write(dict(
            numbers=[1, 2, 3],
            name='test',
            value=0.,
        ), transients)

        time_mock.return_value = 2.
        rec.write(dict(value=2.), transients)

        time_mock.return_value = 3.
        rec.write(dict(action='doit'), transients)

        time_mock.return_value = 4.
        rec.write(dict(action='doit'), transients)

        rec.close()

        with open(f'{basepath}.json') as f:
            info = json.load(f)
        with open(f'{basepath}.ndjson') as f:
            data = [json.loads(line) for line in f.readlines()]
        self.assertEqual(info['id'], 'test_write')
        self.assertEqual(info['signals'], ['action', 'name', 'numbers', 'value'])
        self.assertEqual(info['start'], 0.)
        # self.assertEqual(info['stop'], 4.)
        self.assertEqual(info['name'], '')
        self.assertEqual(data, [
            dict(t=0., numbers=[1, 2, 3], name='test', value=0.),
            dict(t=2., value=2.),
            dict(t=3., action='doit'),
            dict(t=4., action='doit'),
        ])

    @mock.patch('time.time')
    def test_seek(self, time_mock):
        basepath = os.path.join(self.test_dir, 'test_seek')
        rec = recording.Recording(basepath)
        transients = ()
        for i in range(1_000):
            time_mock.return_value = float(i)
            rec.write(dict(i=i), transients)
        rec.close()
        rec = recording.Recording(basepath)
        rec.seek(500.)
        signals = rec.next()
        self.assertLess(abs(signals['t'] - 500.), 2)
