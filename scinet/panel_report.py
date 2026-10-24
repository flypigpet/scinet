"""Render a local panel record without interpreting model claims as verification.

All paper and model content is treated as untrusted text. The report deliberately
links, but never reads or embeds, the commitment: callers seal the completed
report afterwards, so including its root would create a circular dependency.
"""

import html
import json
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit


def _esc(value):
    return html.escape(str(value), quote=True)


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _items(value):
    return value if isinstance(value, list) else []


def _json_block(value, label='查看完整原始记录'):
    raw = json.dumps(value, ensure_ascii=False, indent=2)
    return f'<details><summary>{_esc(label)}</summary><pre>{_esc(raw)}</pre></details>'


def _limitations(value):
    items = _items(value)
    if not items:
        return '<p class="muted">未记录额外限制。</p>'
    return '<ul>' + ''.join(f'<li>{_esc(item)}</li>' for item in items) + '</ul>'


class _Report:
    def __init__(self, run):
        self.run = run
        self.root = run.resolve()

    def path(self, relative):
        """Accept only portable, root-confined artifact paths, never URLs."""
        if not isinstance(relative, str) or not relative:
            return None
        if any(char in relative for char in ('\\', ':', '\x00')):
            return None
        if any(ord(char) < 32 for char in relative):
            return None
        path = PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            return None
        candidate = self.run.joinpath(*path.parts)
        try:
            if not candidate.resolve().is_relative_to(self.root):
                return None
        except (OSError, ValueError, RuntimeError):
            return None
        return candidate

    def exists(self, relative):
        path = self.path(relative)
        return path is not None and path.is_file()

    def file(self, relative, label=None, future=False):
        label = str(relative) if label is None else label
        path = self.path(relative)
        if path is None:
            return f'<span>{_esc(label)} <span class="muted">（不安全路径，未链接）</span></span>'
        if path.is_file() or future:
            href = quote(relative, safe='/')
            return f'<a href="{href}">{_esc(label)}</a>'
        return f'<span>{_esc(label)} <span class="muted">（文件尚未生成）</span></span>'

    def read(self, relative):
        path = self.path(relative)
        if path is None:
            return None, '不安全路径，未读取'
        if not path.is_file():
            return None, '尚未运行：文件尚未生成'
        try:
            value = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, UnicodeError, ValueError) as error:
            return None, f'记录无法读取：{error}'
        if not isinstance(value, dict):
            return None, '记录格式错误：预期 JSON 对象'
        return value, '记录已保存'

    def files(self, prefix=''):
        base = self.path(prefix) if prefix else self.run
        if base is None or not base.is_dir():
            return []
        return sorted(path.relative_to(self.run).as_posix()
                      for path in base.rglob('*') if path.is_file())

    def links(self, relatives):
        return '<ul class="files">' + ''.join(
            f'<li>{self.file(relative)}</li>' for relative in dict.fromkeys(relatives)
        ) + '</ul>'

    def evidence(self, value):
        refs = []
        for value_item in _items(value):
            item = _mapping(value_item)
            refs.append(f'<li>{self.file(item.get("path", ""))}'
                        f' <span class="muted">· {_esc(item.get("locator", "未提供位置"))}</span></li>')
        if not refs:
            return '<p class="muted">未提供证据引用。</p>'
        return '<ul class="evidence">' + ''.join(refs) + '</ul>'

    def call(self, value, missing):
        if value is None:
            return f'<p class="muted">调用{_esc(missing)}</p>'
        labels = [('model_requested', '请求模型'), ('model_resolved', '返回模型'),
                  ('status', '调用状态'), ('started_at_utc', '开始时间（UTC）'),
                  ('finished_at_utc', '完成时间（UTC）')]
        return '<dl>' + ''.join(
            f'<dt>{label}</dt><dd>{_esc(value.get(key) or "未记录")}</dd>'
            for key, label in labels
        ) + '</dl>'

    def reviewer(self, reviewer, index):
        reviewer = _mapping(reviewer)
        reviewer_id = str(reviewer.get('id', f'未命名-{index}'))
        base = f'reviews/{reviewer_id}'
        response, response_status = self.read(f'{base}/response.json')
        call, call_status = self.read(f'{base}/call.json')
        result = (f'<article class="reviewer"><div class="eyebrow">评审者 {_esc(reviewer_id)}</div>'
                  f'<h3>{_esc(reviewer.get("model", "未记录模型"))}</h3>'
                  f'{self.call(call, call_status)}')
        if response is None:
            result += f'<p class="pending">原始评审{_esc(response_status)}。</p>'
        else:
            result += f'<p class="prose lead">{_esc(response.get("summary", "未提供摘要"))}</p>'
            findings = _items(response.get('findings'))
            if not findings:
                result += '<p class="muted">此记录未列出逐条意见，不据此推断论文没有问题。</p>'
            assessment_labels = {'supported': '支持', 'concern': '疑虑', 'uncertain': '不确定'}
            for raw in findings:
                finding = _mapping(raw)
                assessment = finding.get('assessment', '未记录')
                result += (f'<div class="finding"><div class="eyebrow">{_esc(finding.get("id", ""))}'
                           f' · {_esc(assessment_labels.get(str(assessment), assessment))}</div>'
                           f'<h4>{_esc(finding.get("title", "未命名意见"))}</h4>'
                           f'<p class="prose">{_esc(finding.get("explanation", "未提供论证"))}</p>'
                           f'{self.evidence(finding.get("evidence"))}'
                           '<p class="label">建议复算</p>'
                           f'<p class="prose">{_esc(finding.get("proposed_check", "未提出具体检查"))}</p></div>')
            result += '<h4>提出的复算目标</h4>'
            targets = _items(response.get('reproduction_targets'))
            if not targets:
                result += '<p class="muted">未提出复算目标。</p>'
            for raw in targets:
                target = _mapping(raw)
                result += f'<div class="finding"><h4>{_esc(target.get("id", ""))}</h4>'
                for key, label in [('description', '目标'), ('paper_expected', '论文预期'), ('procedure', '步骤')]:
                    result += f'<p class="label">{label}</p><p class="prose">{_esc(target.get(key, "未提供"))}</p>'
                result += self.evidence(target.get('evidence')) + '</div>'
            result += '<h4>该评审者的限制说明</h4>' + _limitations(response.get('limitations'))
            result += _json_block(response, '查看该评审者完整原始 JSON（保留全部字段）')
        result += '<h4>该评审者的调用证据</h4>'
        expected = ['prompt.txt', 'schema.json'] + [f'{base}/{name}' for name in
                    ('response.json', 'events.jsonl', 'stderr.log', 'call.json')]
        result += self.links(expected + self.files(base)) + '</article>'
        return result

    def synthesis(self):
        response, response_status = self.read('synthesis/response.json')
        call, call_status = self.read('synthesis/call.json')
        result = ('<section><h2>复算后的分组与分歧</h2>'
                  '<p class="note">综合是模型判断；它不能覆盖原始意见，也不等同于人类专家验证。'
                  '单一评审者提出的意见，不能据此称为共识。分组与裁决均可回到原始文件质疑。</p>')
        result += self.call(call, call_status)
        if response is None:
            result += f'<p class="pending">综合{_esc(response_status)}；暂不生成分组结论。</p>'
        else:
            result += f'<p class="prose lead">{_esc(response.get("summary", "未提供综合摘要"))}</p>'
            relations = {'agreement': '意见一致', 'disagreement': '保留分歧',
                         'different_scope': '讨论范围不同', 'single_reviewer': '单一评审者'}
            verdicts = {'supported': '支持该评审意见', 'refuted': '反驳该评审意见',
                        'partly_supported': '部分支持该意见', 'unresolved': '该意见仍未解决',
                        'not_tested': '该意见未核验'}
            bases = {'computation': '计算核验', 'source_inspection': '原文核对',
                     'insufficient_evidence': '证据不足'}
            groups = _items(response.get('groups'))
            if not groups:
                result += '<p class="muted">综合记录未提供分组。</p>'
            for raw in groups:
                group = _mapping(raw)
                positions = [_mapping(item) for item in _items(group.get('positions'))]
                reviewer_ids = {str(item.get('reviewer_id')) for item in positions if item.get('reviewer_id')}
                relationship = str(group.get('relationship', '未记录关系'))
                label = relations.get(relationship, relationship)
                if len(reviewer_ids) == 1:
                    label = '单一评审者（不能据此称为共识）'
                elif not reviewer_ids:
                    label = '未列出评审者立场，无法判断一致性'
                result += (f'<article class="group"><div class="eyebrow">{_esc(group.get("id", ""))}'
                           f' · {_esc(label)}</div><h3>{_esc(group.get("title", "未命名分组"))}</h3>'
                           f'<p class="prose">{_esc(group.get("explanation", "未提供解释"))}</p>')
                for position in positions:
                    verdict = str(position.get('verdict', '未记录'))
                    basis = position.get('verification_basis')
                    basis_label = bases.get(str(basis), basis or '未记录核验依据')
                    result += (f'<div class="position"><h4>{_esc(position.get("reviewer_id", "未记录评审者"))}'
                               f' / {_esc(position.get("finding_id", "未记录意见"))}'
                               f' · {_esc(verdicts.get(verdict, verdict))}</h4>'
                               f'<p class="label">核验依据：{_esc(basis_label)}</p>'
                               f'<p class="prose">{_esc(position.get("rationale", "未提供理由"))}</p>'
                               f'{self.evidence(position.get("evidence"))}</div>')
                result += '</article>'
            result += '<h3>综合的限制说明</h3>' + _limitations(response.get('limitations'))
            result += _json_block(response, '查看完整综合 JSON（模型原始分组与全部立场）')
        expected = ['synthesis_prompt.txt', 'synthesis_schema.json'] + [f'synthesis/{name}' for name in
                    ('response.json', 'events.jsonl', 'stderr.log', 'call.json')]
        result += '<h3>综合调用证据</h3>' + self.links(expected + self.files('synthesis'))
        return result + '</section>'


_STYLE = '''
:root{color-scheme:light;--ink:#1c2b3a;--muted:#5f7081;--line:#dbe3e9;--accent:#176b70}
*{box-sizing:border-box}body{margin:0;background:#f3f6f8;color:var(--ink);font:16px/1.75 "Segoe UI","Microsoft YaHei",sans-serif}
main{max-width:1150px;margin:auto;padding:32px 28px 72px}header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:16px}
.brand{font-weight:800;letter-spacing:3px;color:var(--accent)}.hero{padding:30px 0 8px}h1{font-size:34px;line-height:1.35;margin:8px 0 18px}h2{font-size:24px;margin:0 0 14px}h3{font-size:20px;margin:12px 0}h4{font-size:16px;margin:12px 0 6px}
p{margin:8px 0 14px}section,.overview{background:#fff;border:1px solid var(--line);border-radius:12px;padding:26px;margin:22px 0}.eyebrow,.label{color:var(--accent);font-size:13px;font-weight:700}.muted{color:var(--muted);font-size:13px}.lead{font-size:18px}.prose{white-space:pre-wrap;overflow-wrap:anywhere}
.note,.pending{background:#f6f9fb;border-left:3px solid var(--accent);padding:12px 16px}.pending{color:var(--muted)}.reviewer+.reviewer,.group+.group{border-top:2px solid var(--line);margin-top:28px;padding-top:22px}.finding,.position{border-top:1px solid var(--line);padding:14px 0}.position{padding-left:18px}
a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}dl{display:grid;grid-template-columns:170px 1fr;font-size:14px;gap:4px 12px}dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;border-bottom:1px solid var(--line);padding:10px;vertical-align:top;overflow-wrap:anywhere}th{color:var(--muted);background:#f7f9fb}
ul{padding-left:23px}.files,.evidence{font-size:13px}.files{columns:2;column-gap:32px}.files li{break-inside:avoid}details{margin:16px 0}summary{cursor:pointer;color:var(--accent)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7f9;border-radius:8px;padding:18px;font-size:12px;line-height:1.6}footer{color:var(--muted);font-size:12px}
@media(max-width:700px){main{padding:20px 14px 48px}header{display:block}h1{font-size:27px}section,.overview{padding:18px}.files{columns:1}dl{grid-template-columns:115px 1fr}.position{padding-left:10px}}
@media print{body{background:#fff}main{padding:0}section{break-inside:auto}.finding,.position{break-inside:avoid}.files{columns:1}details{display:block}}
'''


def render_panel(run: Path) -> Path:
    """Write ``run/report.html`` from available records and return that path."""
    run = Path(run)
    report = _Report(run)
    panel, panel_status = report.read('panel.json')
    packet, packet_status = report.read('packet.json')
    panel = panel or {}
    packet = packet or {}
    paper = _mapping(panel.get('paper')) or _mapping(packet.get('paper'))
    title = paper.get('title', '论文标题尚未记录')
    reviewers = _items(panel.get('reviewers'))
    content = [f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
               '<meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>SciNet · {_esc(title)} · 多模型证据报告</title><style>{_STYLE}</style>'
               '</head><body><main><header><div class="brand">SCI / NET</div>'
               '<div class="muted">多模型评审 · 冻结记录 · 实际复算 · 保留分歧</div></header>',
               f'<div class="hero"><div class="eyebrow">论文评审与复算记录</div><h1>{_esc(title)}</h1>'
               f'<p>DOI：{_esc(paper.get("doi") or "未提供")}</p>'
               f'<p>流程状态：<strong>{_esc(panel.get("state", "尚未运行"))}</strong></p></div>',
               '<div class="overview"><h2>模型与本次调用状态</h2><p class="muted">'
               '模型名称、状态与时间按原始调用记录展示；未记录的实际模型不由请求名称推断。</p>',
               '<div class="scroll"><table><thead><tr><th>评审者</th><th>配置模型</th><th>请求模型</th>'
               '<th>返回模型</th><th>调用状态</th><th>原始输出</th></tr></thead><tbody>']
    for raw in reviewers:
        reviewer = _mapping(raw)
        reviewer_id = str(reviewer.get('id', '未记录'))
        base = f'reviews/{reviewer_id}'
        call, call_status = report.read(f'{base}/call.json')
        call = call or {}
        values = [reviewer_id, reviewer.get('model', '未记录'), call.get('model_requested', '未记录'),
                  call.get('model_resolved') or '未记录', call.get('status', call_status)]
        content.append('<tr>' + ''.join(f'<td>{_esc(value)}</td>' for value in values)
                       + f'<td>{report.file(f"{base}/response.json", "原始评审 JSON")}</td></tr>')
    if not reviewers:
        content.append('<tr><td colspan="6">尚未配置评审者。</td></tr>')
    content.append('</tbody></table></div><p class="muted">流程约定：每个模型接收相同材料与统一中性提示，'
                   '独立提交意见后冻结，再进行复算与综合。是否遵守约定须核对原始记录。</p></div>')

    content.append('<section><h2>输入材料与统一评审提示</h2>'
                   '<p>材料范围、来源、哈希与是否提供给评审者均保留在输入清单中。</p>')
    content.append(report.links(['panel.json', 'packet.json', 'prompt.txt', 'schema.json']))
    content.append(f'<p class="muted">流程配置：{_esc(panel_status)}；输入清单：{_esc(packet_status)}。</p>')
    for raw in _items(packet.get('files')):
        item = _mapping(raw)
        content.append(f'<article class="finding"><h3>{report.file(item.get("path", ""))}</h3>'
                       f'<p>用途：{_esc(item.get("role", "未记录"))} · 提供给评审者：'
                       f'{_esc({True: "是", False: "否"}.get(item.get("include_in_review"), "未记录"))}</p>'
                       f'<p class="muted">SHA-256：{_esc(item.get("sha256", "未记录"))}</p>')
        source_url = str(item.get('source_url') or '')
        try:
            url = urlsplit(source_url)
            safe_url = url.scheme.lower() in ('http', 'https') and bool(url.hostname)
        except ValueError:
            safe_url = False
        if safe_url:
            content.append(f'<p>来源：<a href="{_esc(source_url)}">{_esc(source_url)}</a></p>')
        elif source_url:
            content.append(f'<p>来源：{_esc(source_url)}（未链接）</p>')
        content.append('</article>')
    content.append('</section><section><h2>独立原始评审</h2><p class="muted">以下完整保留各评审者'
                   '提交的意见、论证和建议；后续复算与综合不改写这些内容。</p>')
    for index, reviewer in enumerate(reviewers, 1):
        content.append(report.reviewer(reviewer, index))
    if not reviewers:
        content.append('<p class="pending">原始评审尚未运行。</p>')
    content.append('</section><section><h2>冻结记录与实际复算</h2>')
    for relative, label in [('reviews_freeze.json', '原始意见冻结'), ('checks/execution.json', '复算执行')]:
        value, status = report.read(relative)
        content.append(f'<h3>{label}</h3><p>{report.file(relative)} · {_esc(status)}</p>')
        if value is not None:
            content.append(_json_block(value, f'查看{label}完整记录'))
    content.append('<h3>计算程序、日志与产物</h3>')
    check_files = report.files('checks')
    content.append(report.links(check_files) if check_files else '<p class="pending">复算尚未运行：文件尚未生成。</p>')
    content.append('</section>')
    content.append(report.synthesis())

    content.append('<section><h2>证据的边界</h2><ul><li>这些意见与综合来自模型判断，可能有误；'
                   '本报告没有人类领域专家复核。</li><li>实际复算的结论只覆盖执行记录中的输入、步骤和产物，'
                   '未执行的检查不能称为验证。</li><li>本地哈希承诺用于检查文件变化，不证明作者身份、'
                   '执行时间或科学正确性，也不是链上证明。</li></ul>')
    content.append(_limitations(panel.get('limitations')) + '</section>')
    content.append('<section><h2>完整证据文件</h2><p>报告完成后重新生成 '
                   + report.file('commitment.json', 'commitment.json（本地内容承诺）', future=True)
                   + '。页面只链接该文件，不嵌入可能过期的根哈希。文件尚未生成时，承诺尚未运行。</p>')
    files = [relative for relative in report.files()
             if relative not in ('report.html', 'commitment.json') and not relative.endswith('.pyc')]
    content.append(report.links(files))
    content.append('</section><footer>SciNet · 保留每一条原始意见，连接复算证据，公开分歧与未解决项。'
                   '</footer></main></body></html>')
    output = run / 'report.html'
    output.write_text('\n'.join(content), encoding='utf-8')
    return output
