"""Read-only AI conversations measured through public API/SSE (stdlib)."""
import argparse
import io
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from datetime import datetime, timezone
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smoke_service_flow import sse_events


def summarize(rows):
    result = {}
    for case in sorted({r['scenario'] for r in rows}):
        group = [r for r in rows if r['scenario'] == case]
        ok = [r for r in group if r['status'] == 'DONE']
        entry = {'attempts': len(group), 'done': len(ok), 'other': len(group)-len(ok)}
        for field in ('accepted_s', 'first_status_s', 'first_token_s', 'elapsed_s'):
            xs = sorted(r[field] for r in ok if r.get(field) is not None)
            entry[field] = {'n': len(xs), 'p50': statistics.median(xs),
                            'p95': xs[math.ceil(.95*len(xs))-1]} if xs else None
        result[case] = entry
    return result


class Client:
    def __init__(self, base):
        self.base, self.token, self.locale = base.rstrip('/'), None, 'en'

    def request(self, path, body=None, stream=False):
        headers = {'Content-Type': 'application/json', 'Accept-Language': self.locale}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        if stream:
            headers['Accept'] = 'text/event-stream'
        return urllib.request.urlopen(urllib.request.Request(self.base + '/api' + path,
            data=json.dumps(body).encode() if body is not None else None, headers=headers), timeout=150 if stream else 30)

    def call(self, path, body=None):
        with self.request(path, body) as response:
            return json.load(response)

    def measure(self, scenario):
        self.locale = scenario['locale']
        result = {'scenario': scenario['id'], 'locale': self.locale, 'status': 'NOT_STARTED',
                  'accepted_s': None, 'first_status_s': None, 'first_token_s': None,
                  'elapsed_s': None, 'events': [], 'duplicate_event_ids': [], 'result_cards': [],
                  'answer': None, 'suggestions': [], 'quality': 'NOT_REVIEWED'}
        conversation = self.call('/ai/conversations', {'hospitalId': None, 'parentConversationId': None})
        result['conversation_id'] = conversation['id']
        started = time.monotonic()
        try:
            task = self.call('/ai/tasks', {'conversationId': conversation['id'],
                'message': scenario['message'], 'action': scenario.get('action')})
            result['task_id'] = task['taskId']
            result['accepted_s'] = time.monotonic()-started
            seen = set()
            with self.request('/ai/tasks/' + task['taskId'] + '/stream', stream=True) as response:
                for event in sse_events(response):
                    elapsed = time.monotonic()-started
                    kind = event.get('event')
                    result['events'].append({'event': kind, 'id': event.get('id'), 'elapsed_s': elapsed})
                    eid = event.get('id')
                    if eid is not None:
                        if eid in seen:
                            result['duplicate_event_ids'].append(eid)
                        seen.add(eid)
                    if kind == 'RESULT_CARDS':
                        result['result_cards'] = event['data'].get('cards', [])
                    if kind == 'STATUS' and result['first_status_s'] is None:
                        result['first_status_s'] = elapsed
                    if kind == 'TOKEN' and event['data'].get('text') and result['first_token_s'] is None:
                        result['first_token_s'] = elapsed
                    if kind in {'DONE', 'FAILED', 'APPROVAL_REQUIRED'}:
                        result['status'], result['elapsed_s'] = kind, elapsed
                        if kind == 'DONE':
                            result['answer'] = event['data'].get('answer')
                            result['suggestions'] = event['data'].get('suggestions', [])
                        elif kind == 'FAILED':
                            result['failure_code'] = event['data'].get('code')
                        break
                    if elapsed > 180:
                        result['status'] = 'CLIENT_DEADLINE'
                        break
                else:
                    result['status'] = 'STREAM_ENDED'
        except Exception as error:
            result['status'] = type(error).__name__
            result['http_status'] = getattr(error, 'code', None)
        if result['elapsed_s'] is None:
            result['elapsed_s'] = time.monotonic()-started
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:18080')
    parser.add_argument('--version')
    parser.add_argument('--commit')
    parser.add_argument('--repeats', type=int, default=10)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--scenarios', type=Path, default=Path(__file__).with_name('scenarios.json'))
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        rows = [{'scenario':'a','status':'DONE','elapsed_s':x} for x in range(1,21)]
        rows.append({'scenario':'a','status':'FAILED','elapsed_s':0})
        s = summarize(rows)['a']
        assert s['done'] == 20 and s['attempts'] == 21 and s['elapsed_s'] == {'n':20,'p50':10.5,'p95':19}
        assert summarize([{'scenario':'b','status':'FAILED'}])['b']['elapsed_s'] is None
        sample = b': ping\n\nid: 1\nevent: TOKEN\ndata: {"text":"ok"}\n\nid: 2\nevent: DONE\ndata: {"answer":"ok"}\n\n'
        assert [e['event'] for e in sse_events(io.BytesIO(sample))] == ['TOKEN','DONE']
        print('SELF_TEST_PASS'); return
    if not args.version or not args.commit or not args.output or args.repeats < 1:
        parser.error('--version, --commit, --output and positive --repeats required')
    cases = json.loads(args.scenarios.read_text())
    accounts = json.loads(Path(os.environ['PERF_ACCOUNTS_FILE']).read_text()) if os.environ.get('PERF_ACCOUNTS_FILE') else {case['locale']: {'email': os.environ['PERF_EMAIL'], 'password': os.environ['PERF_PASSWORD']} for case in cases}
    clients = {}
    for locale in {case['locale'] for case in cases}:
        client = Client(args.base)
        auth = client.call('/auth/login', accounts[locale])
        if auth['user']['locale'] != locale:
            raise ValueError('Account locale must match scenario; Accept-Language does not set agent locale')
        client.token = auth['accessToken']
        clients[locale] = client
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # Exclusive creation prevents accidental loss or mixing of previous experiment results.
    with args.output.open('x') as output:
        for repeat in range(args.offset+1, args.offset+args.repeats+1):
            for case in cases:
                at = datetime.now(timezone.utc).isoformat()
                try:
                    row = clients[case['locale']].measure(case)
                except Exception as error:
                    row = {'scenario':case['id'],'status':'SETUP_' + type(error).__name__, 'elapsed_s':None}
                row.update(version=args.version, commit=args.commit, repeat=repeat, executed_at=at,
                           input=case, concurrency=1, boundary='task_POST_to_SSE_client')
                rows.append(row)
                output.write(json.dumps(row, ensure_ascii=False)+'\n'); output.flush()
                print(args.version, repeat, case['id'], row['status'], row.get('elapsed_s'), flush=True)
                if row['status'] not in {'DONE', 'FAILED', 'APPROVAL_REQUIRED'}:
                    raise RuntimeError('Transport/setup failure: stop to avoid overlapping unfinished tasks')
    args.output.with_suffix('.summary.json').write_text(json.dumps(summarize(rows), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
