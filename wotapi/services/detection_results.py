from datetime import datetime
from itertools import groupby
from pathlib import Path
import random
from time import time
import re
from typing import Any, Mapping, Sequence
from wotapi.models import ResultState

from loguru import logger


class DetectionResultsService:
    def __init__(self, config):
        self.root = Path(config.get('detection_results_service', 'ROOT_PATH'))
        self.thresholds = [
            float(v)
            for v in config.get("detector_service", "THRESHOLDS").split(",")
        ]

    async def get_all_results(self):
        """
        Classification results are stored in a key-value database with
        structure below:

        * All Results
        Key: all
        Values: [
            { date: '20190102', state: 'k_positive' },
            { date: '20190103', state: 'k_negative' },
        ]
        Notes: only dates with data would exists in this list


        * Results by Date
        Key: date in format '20200201'
        Values: [
            { time: ${timestamp in seconds}, state: 'k_positve' }
            { time: ${timestamp in seconds}, state: 'k_negative' }
        ]
        """
        return [
            {
                'date': '20200205',
                'state': 'k_positive'
            },
            {
                'date': '20200203',
                'state': 'k_negative'
            },
            {
                'date': '20200204',
                'state': 'k_negative'
            },
        ]

    async def get_results_by_month(self, month) -> Sequence[Mapping[str, Any]]:
        # expected pattern is: `202006` (stands for June, 2020)
        assert re.match(r'20\d{4}', month) is not None
        assert int(month[-2:], base=10) <= 12

        res = []
        # enumerate all the run results
        for run_results_path in self.root.glob(f'{month}*/'):
            if run_results_path.is_dir():
                # the folder created time with year, month, day, hours, seconds
                run_id = run_results_path.stem
                date = run_id[:len('20201225')]

                # only png pics count as a indentified positive sample
                result_state = self.parse_result_file(run_results_path)

                # per run results
                res.append({'rid': run_id, 'state': result_state, 'date': date})

        keyfunc = lambda x: x['date']

        grouped = groupby(sorted(res, key=keyfunc), key=keyfunc)
        return [{
            'date':
            k,
            'state':
            ResultState.Positive
            if any([r['state'] == ResultState.Positive
                    for r in g]) else ResultState.Negative
        } for k, g in grouped]

    async def get_results_by_date(self, date):
        assert re.match(r'20\d{6}', date) is not None
        assert int(date[len('2020'):len('202012')], base=10) <= 12
        assert int(date[-2:]) <= 31

        res = []
        for run_results_path in self.root.glob(f'{date}*/'):
            if run_results_path.is_dir():
                # the folder created time with year, month, day, hours, seconds
                run_id = run_results_path.stem
                timestamp = int(
                    datetime.strptime(run_id, '%Y%m%d%H%M%S').timestamp())

                # only png pics count as a indentified positive sample
                result_state = self.parse_result_file(run_results_path)

                # per run results
                res.append({
                    'rid': run_id,
                    'state': result_state,
                    'time': timestamp
                })

        return res

    def parse_result_file(self, path: Path) -> ResultState:
        try:
            result_file_path = path / 'results.txt'
            f = result_file_path.open('r')
            for line in f:
                line = line.strip()
                _, filename, label, confidence = line.split(':')
                label = int(label)
                confidence = float(confidence)
                if label > 0 and confidence > self.thresholds[label]:
                    logger.info(
                        f'Find  positive result in {path}: {filename=} {label=} {confidence=}'
                    )
                    return ResultState.Positive

            return ResultState.Negative
        except FileNotFoundError:
            return ResultState.Negative
