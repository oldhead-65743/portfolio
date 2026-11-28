#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静的サイトビルダー。
content/site.toml と content/works/*.md（TOML frontmatter + 日英本文）を読み、
originals/<ID>/ の画像を images/<ID>/ に縮小（ffmpeg）して、全HTML + sitemap + robots を生成する。
依存：Python 標準ライブラリ（tomllib）＋ ffmpeg（PATH 上）。"""
import os, re, json, glob, subprocess, datetime, tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'docs')   # 配信ファイルの出力先（GitHub Pages: main/docs）
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
         'family=Noto+Sans+JP:wght@400;500&family=Noto+Serif+JP:wght@400;500&display=swap">')

def A(s):  # attribute value
    return str(s).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')
def T(s):  # text node
    return str(s).replace('&', '&amp;').replace('<', '&lt;')
def short_title(t):
    return t.split('〜')[0].strip()

# ---------- load data ----------
def load():
    site = tomllib.load(open(os.path.join(ROOT, 'content', 'site.toml'), 'rb'))
    works = {}
    for f in glob.glob(os.path.join(ROOT, 'content', 'works', '*.md')):
        s = open(f, encoding='utf-8').read()
        _, fm, body = s.split('+++', 2)
        d = tomllib.loads(fm)
        d['id'] = os.path.splitext(os.path.basename(f))[0]
        # body -> statement paragraphs
        ja = en = ''
        if '## English' in body:
            pre, en = body.split('## English', 1)
        else:
            pre, en = body, ''
        if '## 日本語' in pre:
            ja = pre.split('## 日本語', 1)[1]
        split = lambda t: [p.strip() for p in re.split(r'\n\s*\n', t.strip()) if p.strip()]
        d['st_ja'] = split(ja)
        d['st_en'] = split(en)
        d['short'] = short_title(d['title'])
        d['materials'] = next((v for k, v in d['info'] if k == '素材'), '')
        d['published'] = bool(d.get('photos'))  # 写真が無い作品は下書き扱い
        works[d['slug']] = d
    return site, works

# ---------- images ----------
def build_images(site, works):
    mx = int(site.get('image_max', 1800))
    vf = ("scale=w='min(%d,iw)':h='min(%d,ih)':"
          "force_original_aspect_ratio=decrease:force_divisible_by=2" % (mx, mx))
    n = 0
    for w in works.values():
        src_dir = os.path.join(ROOT, 'originals', w['id'])
        dst_dir = os.path.join(OUT, 'images', w['id'])
        os.makedirs(dst_dir, exist_ok=True)
        for src in sorted(glob.glob(os.path.join(src_dir, '*.jpg'))):
            dst = os.path.join(dst_dir, os.path.basename(src))
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vf', vf,
                            '-q:v', '2', dst], check=True)
            n += 1
    return n

# ---------- shared html ----------
def head(site, title, desc, path, ogtype, img_rel, jsonld, pfx):
    base = site['base_url'].rstrip('/')
    url = base + '/' + path
    img = base + img_rel
    css = pfx + 'css/style.css'
    out = ['<!doctype html>', '<html lang="ja">', '<head>',
           '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>%s</title>' % T(title), FONTS,
           '<meta name="description" content="%s">' % A(desc)]
    if site.get('google_verification'):
        out.append('<meta name="google-site-verification" content="%s">'
                   % A(site['google_verification']))
    for obj in jsonld:
        out.append('<script type="application/ld+json">\n%s\n</script>'
                   % json.dumps(obj, ensure_ascii=False))
    out += ['<link rel="canonical" href="%s">' % A(url),
            '<meta property="og:type" content="%s">' % ogtype,
            '<meta property="og:site_name" content="%s">' % A(site['site_name']),
            '<meta property="og:locale" content="ja_JP">',
            '<meta property="og:title" content="%s">' % A(title),
            '<meta property="og:description" content="%s">' % A(desc),
            '<meta property="og:url" content="%s">' % A(url),
            '<meta property="og:image" content="%s">' % A(img),
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:title" content="%s">' % A(title),
            '<meta name="twitter:description" content="%s">' % A(desc),
            '<meta name="twitter:image" content="%s">' % A(img),
            '<link rel="stylesheet" href="%s">' % css, '</head>', '<body>',
            '<div class="page">']
    return '\n'.join(out)

def header(site, active, pfx):
    def item(href, label, key):
        cur = ' aria-current="page"' if key == active else ''
        return '      <a href="%s%s"%s>%s</a>' % (pfx, href, cur, label)
    return ('  <header class="site-header">\n'
            '    <a class="brand" href="%sindex.html">\n'
            '      <span class="brand__ja">%s</span>\n'
            '      <span class="brand__en">%s</span>\n'
            '      <span class="brand__portfolio">%s</span>\n'
            '    </a>\n'
            '    <nav class="nav" aria-label="メインメニュー">\n%s\n%s\n%s\n%s\n'
            '    </nav>\n'
            '  </header>' % (pfx, T(site['artist_ja']), T(site['artist_en']),
                             T(site['portfolio_label']),
                             item('works.html', 'Works', 'works'),
                             item('exhibitions.html', 'Exhibitions', 'exhibitions'),
                             item('about.html', 'About', 'about'),
                             item('contact.html', 'Contact', 'contact')))

def footer(site):
    return ('  <footer class="site-footer">\n    <span>%s</span>\n  </footer>\n'
            '</div>' % T(site['copyright']))

def person(site, desc=None):
    base = site['base_url'].rstrip('/')
    ab = site.get('about', {})
    p = {
        "@type": "Person",
        "name": site['artist_ja'],
        # 検索語の揺れ（スペース有無・読み・英名）を網羅して同一人物として認識されやすくする
        "alternateName": [site['artist_en'], "若尾俊", "わかお しゅん", "Shun Wakao"],
        "jobTitle": ["美術作家", "アーティスト"],
        "url": base + '/',
        "nationality": {"@type": "Country", "name": "日本"},
        "workLocation": {"@type": "Place", "name": "長野県安曇野"},
        "knowsAbout": ["インスタレーション", "現代美術", "サイアノタイプ",
                       "自然科学", "アートプロジェクト"],
        "alumniOf": [{"@type": "CollegeOrUniversity", "name": "京都芸術大学大学院"},
                     {"@type": "CollegeOrUniversity", "name": "北里大学"}],
        "sameAs": [site['instagram_url']],
    }
    bp = ab.get('birthplace')
    if bp:
        p["birthPlace"] = {"@type": "Place", "name": re.sub(r'^\d+年', '', bp)}
    if desc:
        p["description"] = desc
    return p

PERSON_DESC = "長野県安曇野を拠点に、自然×科学×身体をテーマとしたインスタレーションを制作する美術作家。"

def _banner(cfg, modifier=''):
    if not cfg.get('enabled'):
        return ''
    cls = 'now-on-view' + ((' ' + modifier) if modifier else '')
    return ('    <a class="%s" href="%s">\n'
            '      <span class="now-on-view__label">%s</span>\n'
            '      <span class="now-on-view__title">%s</span>\n'
            '      <span class="now-on-view__meta">%s</span>\n'
            '      <span class="now-on-view__more">%s</span>\n'
            '    </a>' % (cls, A(cfg['link']), T(cfg['label']), T(cfg['title']),
                         T(cfg['meta']), T(cfg['more'])))

def now_group(site):
    parts = [_banner(resolve_now(site) or {}),
             _banner(resolve_upcoming(site) or {}, 'now-on-view--upcoming')]
    parts = [p for p in parts if p]
    if not parts:
        return ''
    return '    <div class="now-group">\n' + '\n'.join(parts) + '\n    </div>'

def ym_ja(s):
    """'2026.09' -> '2026年9月'（桁揃えなし）。変換できなければそのまま返す。"""
    try:
        y, m = str(s).split('.')
        return '%s年%d月' % (y, int(m))
    except Exception:
        return s

MONTHS_EN = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def period_en(full):
    """'2026年9月12日〜2026年12月6日' -> 'Sep 12 – Dec 6, 2026'。"""
    m = re.match(r'(\d+)年(\d+)月(\d+)日〜(\d+)年(\d+)月(\d+)日', str(full))
    if not m:
        return str(full)
    y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
    end = str(d2) if mo1 == mo2 else '%s %d' % (MONTHS_EN[mo2], d2)
    return '%s %d – %s, %d' % (MONTHS_EN[mo1], d1, end, y2)

def place_from_venue(venue):
    """'会場（県）' -> '県　会場'（作品の『場所』表記を会場から導出）。"""
    m = re.match(r'^(.*?)（([^（）]+)）\s*$', str(venue))
    if m:
        return '%s　%s' % (m.group(2).strip(), m.group(1).strip())
    return str(venue)

def exhibition_by_date(site, date):
    for e in site.get('exhibitions', []):
        if e.get('date') == date:
            return e
    return None

def exhibition_of_work(site, slug):
    for e in site.get('exhibitions', []):
        if slug in (e.get('works') or []):
            return e
    return None

def work_info(site, w):
    """作品の情報行。出展したグループ展があれば 展示・場所 を先頭に導出して付ける。"""
    rows = []
    e = exhibition_of_work(site, w.get('slug'))
    if e:
        rows.append(['展示', '%s（%s）' % (e.get('name', ''), e.get('period', ''))])
        rows.append(['場所', place_from_venue(e.get('venue', ''))])
    rows += [list(r) for r in w.get('info', [])
             if len(r) >= 1 and r[0] not in ('展示', '場所')]
    return rows

def resolve_now(site):
    """now_on_view が参照するグループ展から、表示用の cfg を組み立てる。"""
    nv = site.get('now_on_view', {})
    if not nv.get('enabled'):
        return None
    e = exhibition_by_date(site, nv.get('exhibition'))
    if not e:
        return None
    slug = (e.get('works') or [None])[0]
    return {
        'enabled': True, 'label': 'NOW ON VIEW',
        'title': e.get('name', ''), 'title_en': e.get('name_en', e.get('name', '')),
        'meta': '%s　%s' % (e.get('period', ''), e.get('venue', '')),
        'meta_en': '%s · %s' % (period_en(e.get('period', '')), e.get('venue_en', '')),
        'work_link': ('works/%s.html' % slug) if slug else '',
        'event_url': e.get('event_url', ''),
        'link': nv.get('link', 'exhibitions.html'),
        'more': nv.get('more', '詳しく見る →'),
    }

def resolve_upcoming(site):
    """upcoming（次回展示）の period・venue から表示用 cfg を組み立てる。"""
    up = site.get('upcoming', {})
    if not up.get('enabled'):
        return None
    return {
        'enabled': True, 'label': up.get('label', 'UPCOMING'),
        'title': up.get('title', ''), 'title_en': up.get('title_en', up.get('title', '')),
        'meta': '%s　%s' % (up.get('period', ''), up.get('venue', '')),
        'meta_en': '%s · %s' % (period_en(up.get('period', '')), up.get('venue_en', '')),
        'event_url': up.get('event_url', ''),
        'link': up.get('link', 'exhibitions.html'),
        'more': up.get('more', '詳しく見る →'),
    }

def _exh_box(cfg, modifier='', lang='ja'):
    if not cfg.get('enabled'):
        return ''
    cls = 'exh-now' + ((' ' + modifier) if modifier else '')
    en = (lang == 'en')
    if en:
        aria = 'Upcoming' if modifier else 'Now on view'
    else:
        aria = '次回展示' if modifier else '開催中'
    title = cfg.get('title_en') if en and cfg.get('title_en') else cfg.get('title')
    meta = cfg.get('meta_en') if en and cfg.get('meta_en') else cfg.get('meta')
    links = []
    if cfg.get('work_link'):
        links.append('<a href="%s">%s</a>'
                     % (A(cfg['work_link']), 'Work page →' if en else '作品ページ →'))
    if cfg.get('event_url'):
        links.append('<a href="%s" target="_blank" rel="noopener">%s</a>'
                     % (A(cfg['event_url']), 'Exhibition ↗' if en else '展覧会ページ ↗'))
    links_html = ''
    if links:
        links_html = ('        <p class="exh-now__links">%s</p>\n'
                      % '\n        '.join(links))
    return ('      <section class="%s" aria-label="%s">\n'
            '        <p class="exh-now__label">%s</p>\n'
            '        <p class="exh-now__title">%s</p>\n'
            '        <p class="exh-now__meta">%s</p>\n'
            '%s'
            '      </section>' % (cls, aria, T(cfg['label']), T(title),
                                  T(meta), links_html))

def exh_now_group(site, lang='ja'):
    parts = [_exh_box(resolve_now(site) or {}, '', lang),
             _exh_box(resolve_upcoming(site) or {}, 'exh-now--upcoming', lang)]
    parts = [p for p in parts if p]
    if not parts:
        return ''
    return '    <div class="exh-now-group">\n' + '\n'.join(parts) + '\n    </div>\n\n'

# ---------- pages ----------
def page_index(site, works):
    pfx = ''
    base = site['base_url'].rstrip('/')
    jsonld = [{"@context": "https://schema.org", "@type": "WebSite",
               "name": site['site_name'], "url": base + '/', "inLanguage": "ja",
               "about": {"@type": "Person", "name": site['artist_ja'],
                         "alternateName": site['artist_en']}},
              dict({"@context": "https://schema.org"}, **person(site, PERSON_DESC))]
    desc = ("美術作家 若尾 俊（SHUN WAKAO）のポートフォリオ。長野県安曇野を拠点に、"
            "自然×科学×身体をテーマとしたインスタレーションを制作。代表作《水の囀り》《飴と潮騒》ほか。")
    h = head(site, site['site_name'], desc, '', 'website', '/images/04-mizu/1.jpg', jsonld, pfx)
    slides = [sl for sl in site['slideshow'] if sl.get('slug') in works]
    imgs = []
    for i, sl in enumerate(slides):
        w = works[sl['slug']]
        cls = ' is-active' if i == 0 else ''
        imgs.append('      <img class="slideshow__img%s" src="images/%s/1.jpg" alt="%s" '
                    'data-title="%s" data-year="%s" data-place="%s" data-href="works/%s.html">'
                    % (cls, w['id'], A(sl['alt']), A(sl['title']), A(sl['year']),
                       A(sl['place']), A(sl['slug'])))
    dots = []
    for i, sl in enumerate(slides):
        cls = ' class="is-active"' if i == 0 else ''
        dots.append('        <button type="button"%s data-dot aria-label="%sを表示">'
                    '<span></span></button>' % (cls, A(short_title(sl['title']))))
    s0 = slides[0] if slides else {'title': '', 'year': '', 'place': '', 'slug': ''}
    cap = ('<span class="slide-caption__title">%s</span>　%s　%s'
           % (T(s0['title']), T(s0['year']), T(s0['place'])))
    main = ['  <main class="main main--top">',
            now_group(site),
            '    <div class="slideshow" data-slideshow data-seconds="%d">' % int(site.get('slideshow_seconds', 6)),
            '\n'.join(imgs),
            '      <a class="slideshow__link" data-slide-link href="works/%s.html" aria-label="%sの作品ページを開く"></a>'
            % (A(s0['slug']), A(short_title(s0['title']))),
            '    </div>', '',
            '    <div class="slide-bar">',
            '      <p class="slide-caption" data-slide-caption>%s</p>' % cap,
            '      <div class="dots">', '\n'.join(dots), '      </div>',
            '    </div>', '  </main>']
    main = '\n'.join(x for x in main if x != '')
    return '\n'.join([h, header(site, None, pfx), main, footer(site),
                      '<script src="js/slideshow.js"></script>', '</body>', '</html>', ''])

def page_works(site, works):
    pfx = ''
    order = sorted([w for w in works.values() if w['published']], key=lambda w: -w['order'])  # newest first
    jsonld = [{"@context": "https://schema.org", "@type": "CollectionPage",
               "name": "Works ｜ 若尾 俊",
               "about": {"@type": "Person", "name": site['artist_ja'], "alternateName": site['artist_en']},
               "mainEntity": {"@type": "ItemList", "itemListElement": [
                   {"@type": "ListItem", "position": i + 1,
                    "item": {"@type": "VisualArtwork", "name": w['title']}}
                   for i, w in enumerate(order)]}}]
    desc = ("若尾 俊の作品一覧。《風の花》《祈りより出づ》《飴と潮騒》《水の囀り》"
            "《川を診る》《Snow Cradle》《科学と芸術》の7作品。")
    cards = []
    for w in order:
        a0 = w['photos'][0]['alt']
        cards.append('      <a class="work-card" href="works/%s.html">\n'
                     '        <img src="images/%s/1.jpg" alt="%s">\n'
                     '        <span class="work-card__title">《%s》</span>\n'
                     '        <span class="work-card__meta">%s　%s</span>\n'
                     '      </a>' % (w['slug'], w['id'], A(a0), T(w['title']),
                                     T(w['year']), T(w['materials'])))
    main = ('  <main class="main main--works">\n'
            '    <h1 class="page-title">Works</h1>\n'
            '    <section class="works-grid" aria-label="作品一覧">\n%s\n'
            '    </section>\n  </main>' % '\n'.join(cards))
    h = head(site, 'Works ｜ 若尾 俊 SHUN WAKAO', desc, 'works.html', 'website',
             '/images/04-mizu/1.jpg', jsonld, pfx)
    return '\n'.join([h, header(site, 'works', pfx), main, footer(site), '</body>', '</html>', ''])

def page_work(site, works, w):
    pfx = '../'
    by_order = {x['order']: x for x in works.values() if x['published']}
    older = by_order.get(w['order'] - 1)
    newer = by_order.get(w['order'] + 1)
    art = {"@context": "https://schema.org", "@type": "VisualArtwork",
           "name": w['title'], "dateCreated": str(w['year']), "artMedium": w['materials'],
           "creator": {"@type": "Person", "name": site['artist_ja'], "alternateName": site['artist_en']},
           "description": w['summary'],
           "image": site['base_url'].rstrip('/') + '/images/%s/1.jpg' % w['id'],
           "url": site['base_url'].rstrip('/') + '/works/%s.html' % w['slug']}
    h = head(site, '%s ｜ 若尾 俊 SHUN WAKAO' % w['title'], w['summary'],
             'works/%s.html' % w['slug'], 'article', '/images/%s/1.jpg' % w['id'], [art], pfx)
    p0 = w['photos'][0]
    thumbs = []
    for i, ph in enumerate(w['photos'], 1):
        thumbs.append('        <button type="button" data-thumb data-full="../images/%s/%s" '
                      'data-alt="%s" data-caption="%s" aria-label="%d枚目の写真を表示">'
                      '<img src="../images/%s/%s" alt="%s"></button>'
                      % (w['id'], ph['file'], A(ph['alt']), A(ph['caption']), i,
                         w['id'], ph['file'], A(ph['alt'])))
    info = '\n'.join('        <dt>%s</dt><dd>%s</dd>' % (T(k), T(v))
                     for k, v in work_info(site, w))
    ja = '\n'.join('        <p>　%s</p>' % T(p) for p in w['st_ja'])
    en = '\n'.join('        <p>%s</p>' % T(p) for p in w['st_en'])
    videos = ''
    if w.get('videos'):
        figs = []
        style = ' style="max-width: 552px"' if len(w['videos']) == 1 else ''
        for v in w['videos']:
            figs.append('      <figure class="video"%s>\n'
                        '        <div class="video__frame">\n'
                        '          <img src="../images/%s/%s" alt="%s">\n'
                        '          <span>映像埋め込み予定</span>\n'
                        '        </div>\n'
                        '        <figcaption>%s</figcaption>\n'
                        '      </figure>' % (style, w['id'], v['poster'],
                                             A(v['label']), T(v['label'])))
        videos = ('\n    <section class="videos" aria-label="映像">\n%s\n    </section>\n'
                  % '\n'.join(figs))
    pager = ['    <nav class="work-pager" aria-label="前後の作品">']
    if older:
        pager.append('      <a href="%s.html">← 《%s》</a>' % (older['slug'], T(older['short'])))
    pager.append('      <a class="work-pager__index" href="../works.html">作品一覧</a>')
    if newer:
        pager.append('      <a href="%s.html">《%s》 →</a>' % (newer['slug'], T(newer['short'])))
    pager.append('    </nav>')
    main = ('  <main class="main main--detail">\n'
            '    <section class="viewer" data-viewer aria-label="写真">\n'
            '      <div class="viewer__stage">\n'
            '        <img class="viewer__img" data-viewer-img src="../images/%s/%s" alt="%s">\n'
            '        <button type="button" class="viewer__nav viewer__nav--prev" data-viewer-prev aria-label="前の写真">\n'
            '          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M15 5l-7 7 7 7"></path></svg>\n'
            '        </button>\n'
            '        <button type="button" class="viewer__nav viewer__nav--next" data-viewer-next aria-label="次の写真">\n'
            '          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M9 5l7 7-7 7"></path></svg>\n'
            '        </button>\n'
            '      </div>\n'
            '      <div class="viewer__bar">\n'
            '        <p class="viewer__caption" data-viewer-caption>%s</p>\n'
            '        <p class="viewer__counter" data-viewer-counter>1 / %d</p>\n'
            '      </div>\n'
            '      <div class="thumbs">\n%s\n      </div>\n'
            '    </section>\n\n'
            '    <section class="work-head">\n'
            '      <div class="work-head__title-group">\n'
            '        <h1 class="work-head__title">%s</h1>\n'
            '        <p class="work-head__year">%s</p>\n'
            '      </div>\n'
            '      <dl class="work-meta">\n%s\n      </dl>\n'
            '    </section>\n\n'
            '    <section class="statement">\n'
            '      <div class="statement__ja">\n%s\n      </div>\n'
            '      <div class="statement__en" lang="en">\n%s\n      </div>\n'
            '    </section>\n%s\n%s\n  </main>'
            % (w['id'], p0['file'], A(p0['alt']), T(p0['caption']), len(w['photos']),
               '\n'.join(thumbs), T(w['title']), T(w['year']), info, ja, en, videos,
               '\n'.join(pager)))
    return '\n'.join([h, header(site, 'works', pfx), main, footer(site),
                      '<script src="../js/viewer.js"></script>', '</body>', '</html>', ''])

def page_exhibitions(site, works):
    pfx = ''
    iso = {'2026.09': ('2026-09-12', '2026-12-06'),
           '2025.09': ('2025-09-13', '2025-09-22'), '2025.01': ('2025-01-19', '2025-02-02'),
           '2024.09': ('2024-09-23', '2024-10-01'), '2024.01': ('2024-01-17', '2024-02-01'),
           '2023.09': ('2023-09-17', '2023-09-24')}
    items = []
    for i, e in enumerate(site['exhibitions'], 1):
        st, en = iso.get(e['date'], ('', ''))
        ev = {"@type": "ExhibitionEvent", "name": e['name'], "startDate": st, "endDate": en,
              "location": {"@type": "Place", "name": e['venue'].split('（')[0]}}
        items.append({"@type": "ListItem", "position": i, "item": ev})
    jsonld = [{"@context": "https://schema.org", "@type": "ItemList",
               "name": "Exhibitions ｜ 若尾 俊", "itemListElement": items}]
    desc = ("若尾 俊の展示・ワークショップ・受賞の記録。長野市芸術館アート・グループ展、"
            "AKAP 夏展・冬展、安曇野市×京都芸術大学連携アートプロジェクトほか。")
    MONTHS = ['', 'Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.',
              'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.']
    def date_en(d):
        y, m = d.split('.')
        return '%s %s' % (MONTHS[int(m)], y)
    def wlink(s):
        w = works[s]
        if w['published']:
            return '<a href="works/%s.html">《%s》</a>' % (w['slug'], T(w['title']))
        return '《%s》' % T(w['title'])
    def exh_rows(lang):
        en = (lang == 'en')
        out = []
        for e in site['exhibitions']:
            if en:
                d, name = date_en(e['date']), e.get('name_en', e['name'])
                venue, links = e.get('venue_en', e['venue']), ''
            else:
                d, name = ym_ja(e['date']), e['name']
                venue = e['venue'] + '　' + e.get('period', '')
                links = '　'.join(wlink(s) for s in e['works'])
            out.append('      <div class="exh-row">\n'
                       '        <span class="exh-row__date">%s</span>\n'
                       '        <div class="exh-row__body">\n'
                       '          <span class="exh-row__name">%s</span>\n'
                       '          <span class="exh-row__venue">%s</span>\n'
                       '          <span class="exh-row__works">%s</span>\n'
                       '        </div>\n'
                       '      </div>' % (T(d), T(name), T(venue), links))
        return '\n\n'.join(out)
    ws, aw = site['workshop'], site['award']
    def panel(lang, hidden):
        en = (lang == 'en')
        hid = ' hidden' if hidden else ''
        h_exh = 'Group Exhibitions' if en else 'グループ展'
        h_ws = 'Workshop' if en else 'ワークショップ'
        h_aw = 'Award' if en else '受賞'
        ws_d = date_en(ws['date']) if en else ym_ja(ws['date'])
        ws_t = ws.get('text_en', ws['text']) if en else ws['text']
        aw_d = date_en(aw['date']) if en else ym_ja(aw['date'])
        aw_t = aw.get('text_en', aw['text']) if en else aw['text']
        return ('      <div class="exh-lang" data-lang="%s" lang="%s"%s>\n'
                '%s'
                '    <section class="exh-section">\n'
                '      <h2 class="exh-section__title">%s</h2>\n\n%s\n'
                '    </section>\n\n'
                '    <div class="exh-cols">\n'
                '      <section class="exh-col">\n'
                '        <h2 class="exh-section__title">%s</h2>\n'
                '        <div class="exh-mini">\n'
                '          <span class="exh-mini__date">%s</span>\n          <span>%s</span>\n'
                '        </div>\n'
                '      </section>\n\n'
                '      <section class="exh-col">\n'
                '        <h2 class="exh-section__title">%s</h2>\n'
                '        <div class="exh-mini">\n'
                '          <span class="exh-mini__date">%s</span>\n          <span>%s</span>\n'
                '        </div>\n'
                '      </section>\n'
                '    </div>\n'
                '      </div>'
                % (lang, lang, hid, exh_now_group(site, lang), T(h_exh), exh_rows(lang),
                   T(h_ws), T(ws_d), T(ws_t), T(h_aw), T(aw_d), T(aw_t)))
    main = ('  <main class="main main--exh">\n'
            '    <div class="about-head">\n'
            '      <h1 class="page-title">Exhibitions</h1>\n'
            '      <div class="lang-toggle" role="group" aria-label="表示言語 / Language" data-lang-toggle>\n'
            '        <button type="button" data-lang="ja" aria-pressed="true">日本語</button>\n'
            '        <button type="button" data-lang="en" aria-pressed="false">English</button>\n'
            '      </div>\n'
            '    </div>\n\n'
            '%s\n\n'
            '%s\n'
            '  </main>' % (panel('ja', False), panel('en', True)))
    h = head(site, 'Exhibitions ｜ 若尾 俊 SHUN WAKAO', desc, 'exhibitions.html', 'website',
             '/images/04-mizu/1.jpg', jsonld, pfx)
    return '\n'.join([h, header(site, 'exhibitions', pfx), main, footer(site),
                      '<script src="js/lang.js"></script>', '</body>', '</html>', ''])

def page_about(site):
    pfx = ''
    ab = site['about']
    desc = ("美術作家 若尾 俊（SHUN WAKAO）について。薬剤師でもあり、自然科学の専門性と"
            "地域の自然・素材を活かしたインスタレーションを制作。略歴・学歴・職歴。")
    about_desc = ("1992年東京生まれ。薬学の学位を持つ薬剤師であり、医療機器の研究開発に携わる"
                  "かたわら、長野県安曇野を拠点にインスタレーションを制作する美術作家。"
                  "2025年3月に京都芸術大学大学院を修了。")
    jsonld = [{"@context": "https://schema.org", "@type": "ProfilePage",
               "mainEntity": person(site, about_desc)}]
    def lang_block(lang, bio, cv, head_label, link_label, hidden):
        bios = '\n'.join('          <p>%s%s</p>' % ('　' if lang == 'ja' else '', T(p)) for p in bio)
        rows = '\n'.join('              <span class="about-cv__d">%s</span><span>%s</span>'
                         % (T(ym_ja(a) if lang == 'ja' else a), T(b)) for a, b in cv)
        hid = ' hidden' if hidden else ''
        aria_bio = '略歴' if lang == 'ja' else 'Biography'
        aria_cv = '学歴・職歴' if lang == 'ja' else 'Education / Career'
        return ('      <div class="about-lang" data-lang="%s" lang="%s"%s>\n'
                '        <section class="about-bio" aria-label="%s">\n%s\n        </section>\n'
                '        <section class="about-cv" aria-label="%s">\n'
                '          <div class="about-cv__group">\n'
                '            <h2 class="about-cv__head">%s</h2>\n'
                '            <div class="about-cv__rows">\n%s\n            </div>\n'
                '          </div>\n'
                '          <a class="about-exh-link" href="exhibitions.html">%s</a>\n'
                '        </section>\n'
                '      </div>' % (lang, lang, hid, aria_bio, bios, aria_cv,
                                  T(head_label), rows, T(link_label)))
    ja = lang_block('ja', ab['bio_ja'], ab['cv_ja'], ab['cv_head_ja'], ab['exh_link_ja'], False)
    en = lang_block('en', ab['bio_en'], ab['cv_en'], ab['cv_head_en'], ab['exh_link_en'], True)
    main = ('  <main class="main main--about">\n'
            '    <div class="about-head">\n'
            '      <div class="about-name">\n'
            '        <span class="about-name__ja">%s</span>\n'
            '        <span class="about-name__en">%s</span>\n'
            '      </div>\n'
            '      <div class="lang-toggle" role="group" aria-label="表示言語" data-lang-toggle>\n'
            '        <button type="button" data-lang="ja" aria-pressed="true">日本語</button>\n'
            '        <button type="button" data-lang="en" aria-pressed="false">English</button>\n'
            '      </div>\n'
            '    </div>\n\n'
            '    <div class="about-body">\n'
            '      <!-- 日本語 -->\n%s\n\n'
            '      <!-- English -->\n%s\n'
            '    </div>\n  </main>'
            % (T(site['artist_ja']), T(site['artist_en']), ja, en))
    h = head(site, 'About ｜ 若尾 俊 SHUN WAKAO', desc, 'about.html', 'profile',
             '/images/04-mizu/1.jpg', jsonld, pfx)
    return '\n'.join([h, header(site, 'about', pfx), main, footer(site),
                      '<script src="js/lang.js"></script>', '</body>', '</html>', ''])

def page_contact(site):
    pfx = ''
    desc = ("若尾 俊へのお問い合わせ。展示・制作のご依頼、取材などはフォームよりご連絡ください。"
            "Instagram: %s。" % site['instagram_handle'])
    jsonld = [dict({"@context": "https://schema.org"}, **person(site))]
    ig = site['instagram_url']; igh = site['instagram_handle']
    cc = site.get('contact', {})
    maint = bool(cc.get('maintenance'))
    intro = (T(cc.get('maintenance_note', '')) if maint else T(site['contact_intro']))
    dis = ' disabled' if maint else ''
    form = ('    <form class="contact-form%s">\n'
            '      <div class="contact-field">\n'
            '        <label for="c-name">お名前 Name</label>\n'
            '        <input id="c-name" name="name" type="text" autocomplete="name"%s>\n'
            '      </div>\n'
            '      <div class="contact-field">\n'
            '        <label for="c-mail">メールアドレス Email</label>\n'
            '        <input id="c-mail" name="email" type="email" autocomplete="email"%s>\n'
            '      </div>\n'
            '      <div class="contact-field">\n'
            '        <label for="c-body">内容 Message</label>\n'
            '        <textarea id="c-body" name="message" rows="8"%s></textarea>\n'
            '      </div>\n'
            '      <button type="button" class="contact-submit"%s>送信する</button>\n'
            '    </form>'
            % ((' is-maintenance' if maint else ''), dis, dis, dis, dis))
    if maint:
        form = ('    <div class="contact-form-wrap">\n'
                '%s\n'
                '      <div class="contact-cover" role="status">\n'
                '        <span class="contact-cover__badge">%s</span>\n'
                '      </div>\n'
                '    </div>' % (form, T(cc.get('maintenance_label', '整備中'))))
    main = ('  <main class="main main--contact">\n'
            '    <div class="contact-intro">\n'
            '      <h1 class="page-title">Contact</h1>\n'
            '      <p>%s</p>\n'
            '    </div>\n\n'
            '    <!--\n'
            '      TODO: 送信先が未確定です。Formspree 等に接続する場合は、\n'
            '      1) 下の <form> に action="https://formspree.io/f/xxxxxxxx" method="POST" を設定し、\n'
            '      2) 送信ボタンを type="button" から type="submit" に変更し、\n'
            '      3) site.toml の [contact] maintenance を false にしてください。\n'
            '    -->\n'
            '%s\n\n'
            '    <div class="contact-sns">\n'
            '      <span class="contact-sns__label">Instagram</span>\n'
            '      <a href="%s" target="_blank" rel="noopener" aria-label="Instagram %s（別タブで開く）">\n'
            '        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="0.8" fill="currentColor"></circle></svg>\n'
            '        %s\n'
            '      </a>\n'
            '    </div>\n  </main>'
            % (intro, form, A(ig), A(igh), T(igh)))
    h = head(site, 'Contact ｜ 若尾 俊 SHUN WAKAO', desc, 'contact.html', 'website',
             '/images/04-mizu/1.jpg', jsonld, pfx)
    return '\n'.join([h, header(site, 'contact', pfx), main, footer(site), '</body>', '</html>', ''])

def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(content)

def build_sitemap_robots(site, works):
    base = site['base_url'].rstrip('/')
    today = datetime.date.today().isoformat()
    paths = ['', 'works.html', 'exhibitions.html', 'about.html', 'contact.html']
    paths += ['works/%s.html' % w['slug'] for w in sorted(works.values(), key=lambda w: w['order']) if w['published']]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in paths:
        sm.append('  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>' % (base, p, today))
    sm.append('</urlset>\n')
    write('sitemap.xml', '\n'.join(sm))
    write('robots.txt', 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % base)

def main():
    site, works = load()
    nimg = build_images(site, works)
    write('index.html', page_index(site, works))
    write('works.html', page_works(site, works))
    write('exhibitions.html', page_exhibitions(site, works))
    write('about.html', page_about(site))
    write('contact.html', page_contact(site))
    for w in works.values():
        if w['published']:
            write('works/%s.html' % w['slug'], page_work(site, works, w))
    build_sitemap_robots(site, works)
    print('built: 5 + %d work pages | images resized: %d' % (len(works), nimg))

if __name__ == '__main__':
    main()
