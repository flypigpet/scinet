import html
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote

try:
    from scinet.panel_report import render_panel
except ImportError:
    render_panel = None


class ParsedReport(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.links = []
        self.text = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'a':
            self.links.append(dict(attrs).get('href'))

    def handle_data(self, data):
        self.text.append(data)


class PanelReportTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(render_panel, 'panel report implementation is required')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        self.write_json('panel.json', {
            'paper': {'title': '独立审阅的论文', 'doi': '10.1234/example'},
            'state': 'reviews_frozen',
            'reviewers': [{'id': 'r1', 'model': 'model-one'},
                          {'id': 'r2', 'model': 'model-two'}],
            'limitations': ['只覆盖本次提交的材料'],
        })
        self.write_json('packet.json', {'paper': {'title': '独立审阅的论文'}, 'files': []})

    def write_json(self, relative, data):
        self.write_file(relative, json.dumps(data, ensure_ascii=False))

    def write_file(self, relative, text='artifact'):
        path = self.run / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def render(self):
        result = render_panel(self.run)
        self.assertEqual(result, self.run / 'report.html')
        source = result.read_text(encoding='utf-8')
        return source, ParsedReport(source)

    def review(self, reviewer, summary, explanation, assessment='concern'):
        self.write_json(f'reviews/{reviewer}/response.json', {
            'summary': summary,
            'findings': [{'id': 'F1', 'title': summary + '标题',
                          'assessment': assessment, 'explanation': explanation,
                          'evidence': [{'path': 'inputs/paper.txt', 'locator': '第 3 页'}],
                          'proposed_check': '按原始定义重新计算'}],
            'reproduction_targets': [{'id': 'T1', 'description': '计算目标全文',
                                     'paper_expected': '论文预期全文',
                                     'procedure': '复算步骤全文',
                                     'evidence': [{'path': 'inputs/paper.txt', 'locator': '表 1'}]}],
            'limitations': ['评审范围限制全文'],
        })

    def test_preserves_every_original_opinion_separately_from_synthesis(self):
        self.review('r1', '第一位原始摘要', '第一位支持该统计量的完整论证', 'supported')
        self.review('r2', '第二位原始摘要', '第二位反对该统计量的完整论证')
        self.write_json('synthesis/response.json', {
            'summary': '复算后仍有分歧',
            'groups': [{'id': 'G1', 'title': '统计量分歧', 'relationship': 'disagreement',
                        'explanation': '两种定义有不同适用范围',
                        'positions': [
                            {'reviewer_id': 'r1', 'finding_id': 'F1', 'verdict': 'supported',
                             'rationale': '第一位复算依据', 'evidence': []},
                            {'reviewer_id': 'r2', 'finding_id': 'F1', 'verdict': 'unresolved',
                             'rationale': '第二位仍未解决的理由', 'evidence': []}]}],
            'limitations': ['综合判断的范围'],
        })
        source, parsed = self.render()
        for text in ('第一位原始摘要', '第一位支持该统计量的完整论证', '第二位原始摘要',
                     '第二位反对该统计量的完整论证', '按原始定义重新计算', '计算目标全文',
                     '论文预期全文', '复算步骤全文', '评审范围限制全文', '复算后仍有分歧',
                     '第一位复算依据', '第二位仍未解决的理由', '综合判断的范围'):
            self.assertIn(text, ''.join(parsed.text))
        self.assertLess(source.index('第一位原始摘要'), source.index('复算后仍有分歧'))
        self.assertLess(source.index('第二位原始摘要'), source.index('复算后仍有分歧'))
        self.assertIn('模型判断', ''.join(parsed.text))

    def test_missing_stages_show_not_run_and_model_information_comes_first(self):
        self.write_json('reviews/r1/call.json', {
            'model_requested': 'model-one', 'model_resolved': 'actual-model-one',
            'status': 'failed', 'started_at_utc': '2026-10-24T01:00:00Z',
            'finished_at_utc': '2026-10-24T01:02:00Z',
        })
        source, parsed = self.render()
        text = ''.join(parsed.text)
        for expected in ('model-one', 'model-two', 'actual-model-one', 'failed',
                         'reviews_frozen', '尚未运行', '尚未生成', '独立原始评审'):
            self.assertIn(expected, text)
        self.assertLess(source.index('actual-model-one'), source.index('独立原始评审'))
        self.assertIn('综合尚未运行', text)
        self.assertIn('没有人类领域专家复核', text)
        self.assertIn('不是链上证明', text)

    def test_escapes_all_paper_model_and_evidence_text(self):
        attack = '<img src=x onerror="alert(1)"><script>alert(2)</script>&\''
        self.write_json('panel.json', {'paper': {'title': attack, 'doi': attack},
                                     'state': attack,
                                     'reviewers': [{'id': 'r1', 'model': attack}],
                                     'limitations': [attack]})
        self.review('r1', attack, attack, attack)
        self.write_json('reviews/r1/call.json', {'model_requested': attack,
                                               'model_resolved': attack, 'status': attack})
        self.write_json('packet.json', {'paper': {'title': attack}, 'files': [
            {'path': 'inputs/paper.txt', 'sha256': attack, 'source_url': 'javascript:' + attack,
             'role': attack, 'include_in_review': True}]})
        self.write_json('synthesis/response.json', {'summary': attack, 'groups': [
            {'id': attack, 'title': attack, 'relationship': attack, 'explanation': attack,
             'positions': [{'reviewer_id': attack, 'finding_id': attack, 'verdict': attack,
                            'rationale': attack, 'evidence': [{'path': attack, 'locator': attack}]}]}],
            'limitations': [attack]})
        source, parsed = self.render()
        self.assertIn(html.escape(attack, quote=True), source)
        self.assertNotIn('<script', source)
        self.assertNotIn('<img', source)
        for tag, attrs in parsed.tags:
            self.assertFalse(any(name.lower().startswith('on') for name in attrs), (tag, attrs))
        self.assertFalse(any(link.startswith('javascript:') for link in parsed.links))

    def test_links_all_evidence_with_safe_url_encoding_without_old_commitment_root(self):
        filename = 'inputs/材料 #1 & %20.txt'
        files = ['panel.json', 'packet.json', filename, 'reviews_freeze.json',
                 'prompt.txt', 'schema.json', 'synthesis_prompt.txt', 'synthesis_schema.json',
                 'checks/execution.json', 'checks/artifacts/result.csv', 'checks/program.py',
                 'synthesis/prompt.txt', 'synthesis/response.json', 'synthesis/events.jsonl',
                 'synthesis/stderr.log', 'synthesis/call.json', 'timeline.jsonl', 'commitment.json']
        files += [f'reviews/r1/{name}' for name in
                  ('prompt.txt', 'response.json', 'events.jsonl', 'stderr.log', 'call.json')]
        for relative in files:
            if not (self.run / relative).exists():
                self.write_file(relative, '{}' if relative.endswith('.json') else 'artifact')
        self.write_json('packet.json', {'paper': {}, 'files': [
            {'path': filename, 'sha256': 'a' * 64, 'source_url': 'https://example.org/paper?a=1&b=2',
             'role': 'paper', 'include_in_review': True}]})
        old_hash = 'deadbeef' * 8
        self.write_json('commitment.json', {'root_sha256': old_hash})
        source, parsed = self.render()
        for relative in files:
            self.assertIn(quote(relative, safe='/'), parsed.links, relative)
        self.assertNotIn(old_hash, source)
        self.assertIn('https://example.org/paper?a=1&b=2', parsed.links)

    def test_unsafe_paths_are_text_only_and_absent_artifacts_are_identified(self):
        paths = ['../outside.txt', '/etc/passwd', 'C:/outside.txt',
                 'inputs\\paper.txt', 'javascript:alert(1)', '//example.org/file']
        self.write_json('packet.json', {'files': [
            {'path': path, 'source_url': 'javascript:alert(1)'} for path in paths]})
        self.review('r1', '保留证据引用', '尚无证据文件')
        source, parsed = self.render()
        for path in paths:
            self.assertNotIn(path, parsed.links)
            self.assertNotIn(quote(path, safe='/'), parsed.links)
            self.assertIn(html.escape(path, quote=True), source)
        self.assertIn('不安全路径', ''.join(parsed.text))
        self.assertIn('文件尚未生成', ''.join(parsed.text))
        self.assertIn('commitment.json', parsed.links)

    def test_single_reviewer_group_is_not_promoted_to_consensus(self):
        self.review('r1', '一个模型提出的意见', '一个模型的论证')
        self.write_json('synthesis/response.json', {
            'summary': '只有一位评审者提出此问题',
            'groups': [{'id': 'G1', 'title': '单人问题', 'relationship': 'agreement',
                        'explanation': '综合模型使用了 agreement 标签',
                        'positions': [{'reviewer_id': 'r1', 'finding_id': 'F1',
                                       'verdict': 'supported', 'rationale': '复算支持', 'evidence': []}]}],
            'limitations': [],
        })
        source, parsed = self.render()
        self.assertIn('单一评审者', ''.join(parsed.text))
        self.assertIn('不能据此称为共识', ''.join(parsed.text))
        self.assertNotIn('多模型共识', source)

    def test_synthesis_labels_verification_basis_and_verdicts_target_review_opinions(self):
        positions = []
        for basis, verdict in [('computation', 'supported'), ('source_inspection', 'refuted'),
                               ('insufficient_evidence', 'partly_supported'), (None, 'not_tested')]:
            position = {'reviewer_id': 'r1', 'finding_id': verdict, 'verdict': verdict,
                        'rationale': '核对意见而非给论文打分', 'evidence': []}
            if basis:
                position['verification_basis'] = basis
            positions.append(position)
        self.write_json('synthesis/response.json', {
            'summary': '区分核验来源',
            'groups': [{'id': 'G1', 'title': '核验来源', 'relationship': 'single_reviewer',
                        'explanation': '每项单独给出依据', 'positions': positions}],
            'limitations': [],
        })
        source, parsed = self.render()
        for expected in ('计算核验', '原文核对', '证据不足', '未记录核验依据',
                         '支持该评审意见', '反驳该评审意见', '部分支持该意见'):
            self.assertIn(expected, ''.join(parsed.text))


if __name__ == '__main__':
    unittest.main()
