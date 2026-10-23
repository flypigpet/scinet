"""Human-readable, self-contained visual report; evidence remains separate and linked."""
import base64
import csv
import html
import io
import json
from pathlib import Path
from urllib.parse import quote

from .evidence import read_json

def esc(value): return html.escape(str(value), quote=True)

def figures(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups={}
    with (run/'DatasaurusDozen.tsv').open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f,delimiter='\t'): groups.setdefault(r['dataset'],[]).append((float(r['x']),float(r['y'])))
    names=['dino']+sorted(set(groups)-{'dino'})
    fig,axes=plt.subplots(3,5,figsize=(15,9),layout='constrained')
    fig.patch.set_facecolor('#f8fafc')
    for ax in axes.flat: ax.set_visible(False)
    for ax,name in zip(axes.flat,names):
        ax.set_visible(True); xs,ys=zip(*groups[name]); ax.scatter(xs,ys,s=13,c='#087f8c',alpha=.9,linewidths=0)
        ax.set(xlim=(-5,105),ylim=(-5,105)); ax.set_aspect('equal'); ax.set_title(name,fontsize=12,loc='left',fontweight='bold')
        ax.set_xticks([0,50,100]); ax.set_yticks([0,50,100]); ax.tick_params(labelsize=8,colors='#64748b')
        ax.grid(alpha=.18); ax.spines[['top','right']].set_visible(False)
    axes.flat[-1].set_visible(True); axes.flat[-1].axis('off')
    axes.flat[-1].text(0,.8,'13 datasets\n142 points each\n1,846 observations',fontsize=16,color='#0f172a',linespacing=1.7)
    axes.flat[-1].text(0,.25,'Same summary constraints.\nDifferent spatial structure.\nReplotted from author data.',fontsize=10,color='#64748b',linespacing=1.6)
    buf=io.BytesIO(); fig.savefig(buf,format='png',dpi=150,facecolor=fig.get_facecolor()); plt.close(fig)
    data=buf.getvalue(); (run/'scatterplots.png').write_bytes(data)
    return 'data:image/png;base64,'+base64.b64encode(data).decode()

def render(run):
    run=Path(run); m=read_json(run/'metrics.json'); meta=read_json(run/'run.json'); smoke=read_json(run/'author_smoke.json')
    review=read_json(run/'review.json') if (run/'review.json').exists() and meta['ai_review_status']=='fresh_completed' else None
    plot=figures(run)
    stats_rows=''.join('<tr><td>'+esc(s['dataset'])+'</td><td>'+str(s['n'])+'</td>'+''.join('<td>'+f'{s[k]:.10f}'+'</td>' for k in ('mean_x','mean_y','sd_x','sd_y','r'))+'</tr>' for s in m['stats'])
    checks=''
    for key,label in [('floor_2dp','作者代码：向下取整'),('round_2dp','常规理解：四舍五入'),('truncate_2dp','另一种显示约定：向零截断')]:
        v=m['precision'][key]
        checks+=f'<div class="check"><div><b>{label}</b><p>比较 13 组的全部五项统计量。</p></div><span class="badge {"good" if v["passed"] else "warn"}">{"全部相同" if v["passed"] else "并非全部相同"}</span></div>'
    findings=''
    labels={'supported':'支持','qualified':'有条件支持','unsupported':'不支持','not_tested':'未验证'}
    if review:
        for f in review['findings']:
            refs=' · '.join(f'<a href="{quote(e["path"],safe="/")}">{esc(e["path"])} · {esc(e["locator"])}</a>' for e in f['evidence'])
            findings+=f'<article class="finding"><div class="eyebrow">{esc(f["id"])} / {esc(f["claim_id"])} · {labels[f["status"]]}</div><h3>{esc(f["title"])}</h3><p>{esc(f["explanation"])}</p><div class="refs">{refs}</div></article>'
    else: findings='<p>本次仅运行了计算，尚未调用 AI。没有用模板或缓存冒充新评审。</p>'
    limits=['仅覆盖图 6 的数据统计与一次有界算法试运行，没有重做全文实验、全部动画或作者当年的运行时间基准。',
            '复算一致说明当前文件和实现的计算一致；不等于新的独立实验、通用科学认证或期刊替代能力。',
            '本次仅有一个模型评审者，没有独立模型投票，也没有人类领域专家复核。' if review else '本次未运行 AI 评审。',
            '提示词已提醒检查精度规则与网页/论文的区别；这是受引导的审计，不能证明 AI 独立发现未知问题。此知名案例也不能排除模型训练记忆影响。',
            '固定版本的作者代码在本机独立进程运行；当前原型不具备面向任意上传代码的安全沙箱。',
            '文件哈希用于发现内容变化，不能证明作者身份或抵御连同清单一起被改写；本次没有签名或上链。']
    if review: limits+=review['limitations']
    files=sorted(p.relative_to(run).as_posix() for p in run.rglob('*') if p.is_file() and p.name not in ('report.html','manifest.json') and not p.name.endswith('.pyc'))
    links=''.join(f'<li><a href="{quote(p,safe="/")}">{esc(p)}</a></li>' for p in files)
    dino=next(s for s in m['stats'] if s['dataset']=='dino')
    title='统计约束成立，表述需要澄清' if m['precision']['floor_2dp']['passed'] else '发现统计约束差异'
    intro=review['summary'] if review else '已完成实际数据复算；AI 评审待运行。请将此页面视为计算报告。'
    if not m['crosscheck']['passed'] or smoke.get('status')!='passed':
        title='计算流程未通过，暂不能形成结论'
        intro='独立数值交叉核对或作者算法执行未通过。本页保留失败记录；请先解决执行问题，再形成评审结论。'
    markup='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SciNet · 实验 001 · 论文复算与证据报告</title><style>
:root{color-scheme:light;--ink:#15263b;--muted:#617188;--line:#dbe4e9;--teal:#087f8c}*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:var(--ink);font:16px/1.8 "Segoe UI","Microsoft YaHei",sans-serif}main{max-width:1160px;margin:auto;padding:44px 28px 80px}header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:20px;font-size:13px;color:var(--muted)}.brand{letter-spacing:3px;font-weight:750;color:var(--teal)}.hero{padding:45px 0 30px}.eyebrow{font-size:12px;letter-spacing:1px;color:var(--teal);font-weight:700}h1{font-size:38px;line-height:1.35;margin:12px 0 20px;letter-spacing:-1px}h2{font-size:23px;margin:0 0 12px}h3{font-size:18px;margin:6px 0 10px}p{margin:8px 0 14px}.lede{max-width:960px;font-size:18px}.muted,.caption{color:var(--muted);font-size:13px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:25px 0}.card,section{background:white;border:1px solid var(--line);border-radius:14px}.card{padding:22px}.number{font:600 31px/1.3 "Segoe UI",sans-serif;color:var(--teal)}.card p{margin:5px 0 0;font-size:13px;color:var(--muted)}section{padding:28px;margin-top:22px}a{color:var(--teal);text-underline-offset:4px;overflow-wrap:anywhere}.badge{display:inline-block;white-space:nowrap;border-radius:30px;padding:4px 11px;font-size:12px;font-weight:650}.good{color:#087858;background:#e7f6ef}.warn{color:#946200;background:#fff3d7}.check{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:16px 0;border-bottom:1px solid var(--line)}.check p{font-size:13px;color:var(--muted);margin:3px 0}.note{border-left:3px solid #d5a72d;padding:10px 18px;background:#fffbef;margin-top:18px}img{max-width:100%;height:auto;display:block;border-radius:8px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}th,td{padding:12px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--muted);font-weight:600;background:#f8fafc}.finding{border-top:1px solid var(--line);padding:22px 0 8px}.refs{font-size:12px;color:var(--muted)}details{margin-top:16px}summary{cursor:pointer;color:var(--teal)}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;background:#f8fafc;padding:18px;border-radius:8px}ul{padding-left:22px}.files{columns:2;font-size:13px}.footer{font-size:12px;color:var(--muted);padding-top:25px}@media(max-width:700px){main{padding:22px 16px}.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:29px}section{padding:20px}.files{columns:1}header{display:block}.check{align-items:flex-start}.lede{font-size:16px}}@media print{body{background:white}main{padding:0}section,.finding{break-inside:avoid}.files{columns:1}}
</style><main>'''
    markup+=f'<header><div class="brand">SCI / NET</div><div>实验 001 · 单篇论文审计原型 · {esc(meta["created_at_utc"])}</div></header>'
    markup+=f'<div class="hero"><div class="eyebrow">EVIDENCE BEFORE VERDICT</div><h1>{title}</h1><p class="lede">{esc(intro)}</p><p class="muted">Matejka &amp; Fitzmaurice · Same Stats, Different Graphs · CHI 2017 · DOI <a href="https://doi.org/10.1145/3025453.3025912">10.1145/3025453.3025912</a></p></div>'
    markup+='<div class="cards">'+''.join(f'<div class="card"><div class="number">{a}</div><p>{b}</p></div>' for a,b in [(str(m['dataset_count']),'数据组 / 每组 142 个点'),(f'{m["rows"]:,}','真实数据点'),('65','统计量 / 两种实现交叉核对'),('1' if review else '0','本次新生成的 AI 评审')])+'</div>'
    markup+=f'<section><h2>先看真实数据</h2><p class="caption">从固定版本的作者 TSV 重新绘制；没有使用论文里的图片替代本次输出。坐标范围与纵横比例统一。</p><img src="{plot}" alt="作者公开的13组数据，本次重新绘制的散点图"></section>'
    markup+=f'<section><h2>“两位小数相同”究竟怎样计算？</h2>{checks}<div class="note">原始 dino 的样本标准差 sₓ = {dino["sd_x"]:.10f}，相关系数 r = {dino["r"]:.10f}。向下取整、向零截断和四舍五入不是同一运算；负数尤其需要区分。这里分别检验各约定，不把显示差异夸大为主要结论失效。</div><p class="caption">独立实现：Python 标准库与 NumPy/Pandas；最大绝对差 {m["crosscheck"]["max_abs_error"]:.3g}，容差 {m["crosscheck"]["tolerance"]:.1g}。</p><details><summary>查看全部精度比较结果</summary><pre>{esc(json.dumps(m["precision"],ensure_ascii=False,indent=2))}</pre></details></section>'
    markup+=f'<section><h2>全部复算数值</h2><p class="caption">标准差采用样本定义（ddof=1）；Pearson r 不依赖标准差显示方式。</p><div class="scroll"><table><thead><tr><th>数据组</th><th>n</th><th>mean x</th><th>mean y</th><th>sample SD x</th><th>sample SD y</th><th>Pearson r</th></tr></thead><tbody>{stats_rows}</tbody></table></div></section>'
    smoke_summary=(f'完成 {smoke["iterations_completed"]:,} 次提案，接受 {smoke["accepted_proposals"]} 次；{smoke["moved_points"]} 个点发生移动，五项统计约束保持。' if smoke.get('status')=='passed' else '执行未通过：'+str(smoke.get('status','无结果')))
    markup+=f'<section><h2>作者算法的实际试运行</h2><p><strong>{esc(smoke_summary)}</strong></p><p>固定随机种子，在原作者数值函数基础上做有界试运行。适配明细、起止统计和运行日志保存在证据包中；这不是论文全部退火过程的重现。</p><details><summary>查看执行结果与兼容性改动</summary><pre>{esc(json.dumps(smoke,ensure_ascii=False,indent=2))}</pre></details></section>'
    markup+=f'<section><h2>AI 评审：逐条连接到证据</h2><p class="caption">{"实际调用已完成，提示词、输入哈希和原始输出均已留存。单一模型的判断仍可能有误。" if review else "尚未运行 AI。"}</p>{findings}</section>'
    markup+='<section><h2>本次证据的边界</h2><ul>'+''.join('<li>'+esc(x)+'</li>' for x in limits)+'</ul></section>'
    markup+=f'<section><h2>证据文件与运行来源</h2><p>作者代码固定提交：<a href="https://github.com/jmatejka/same-stats-different-graphs/tree/{esc(meta["upstream_commit"])}">{esc(meta["upstream_commit"])}</a>。<a href="manifest.json">SHA-256 清单</a>覆盖本次输入、实现快照与输出；这是本地内容校验，不是身份认证。</p><details><summary>展开全部证据文件</summary><ul class="files">{links}</ul></details><details><summary>环境版本</summary><pre>{esc(json.dumps(meta,ensure_ascii=False,indent=2))}</pre></details></section>'
    markup+='<div class="footer">SciNet MVP · 证据优先，可质疑、可重算。没有期刊等级、综合质量分或自动录用决定。</div></main></html>'
    (run/'report.html').write_text(markup,encoding='utf-8')
