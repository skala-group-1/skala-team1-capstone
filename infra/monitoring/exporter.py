"""Expose immutable experiment rows, not application internals, as Prometheus gauges."""
import json
import math
import os
from pathlib import Path
import statistics
from http.server import BaseHTTPRequestHandler, HTTPServer

NOTICES = ('Unable to complete this request.', '暂时无法完成请求', '処理できませんでした', '요청을 처리하지 못')

def metrics(root):
    groups = {}
    for path in sorted(root.glob('*.jsonl')):
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue  # A writer may not yet have finished the last line.
            if row.get('version') not in ('before', 'after'):
                continue
            groups.setdefault((row['version'], row['scenario']), []).append(row)
    out = []
    for name in ('perf_attempts', 'perf_done', 'perf_unavailable_answers', 'perf_duplicate_events', 'perf_completed_seconds'):
        out.extend([f'# HELP {name} External synthetic experiment; DONE is not a quality verdict.', f'# TYPE {name} gauge'])
    for (version, case), rows in sorted(groups.items()):
        labels = f'version={json.dumps(version)},scenario={json.dumps(case)}'
        done = [r for r in rows if r['status'] == 'DONE']
        values = {'perf_attempts':len(rows),'perf_done':len(done),
                  'perf_unavailable_answers':sum(any(s in (r.get('answer') or '') for s in NOTICES) for r in rows),
                  'perf_duplicate_events':sum(len(r.get('duplicate_event_ids', [])) for r in rows)}
        out.extend(f'{name}{{{labels}}} {value}' for name,value in values.items())
        for stage in ('accepted_s','first_status_s','first_token_s','elapsed_s'):
            xs = sorted(r[stage] for r in done if r.get(stage) is not None)
            if xs:
                for q, value in [('0.5',statistics.median(xs)),('0.95',xs[math.ceil(.95*len(xs))-1])]:
                    out.append(f'perf_completed_seconds{{{labels},stage="{stage}",quantile="{q}"}} {value}')
    return '\n'.join(out)+'\n'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/metrics':
            self.send_error(404); return
        body = metrics(Path(os.environ.get('RESULTS_DIR','/results'))).encode()
        self.send_response(200)
        self.send_header('Content-Type','text/plain; version=0.0.4; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *args):
        pass

if __name__ == '__main__':
    HTTPServer(('0.0.0.0',9100),Handler).serve_forever()
