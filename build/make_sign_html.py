# -*- coding: utf-8 -*-
import io, os

SRC = os.path.expanduser('~/mnt/Github/order-approval-system/src/customer/C10_page.html')
DST = os.path.expanduser('~/mnt/Github/order-sign-page/sign.html')
s = io.open(SRC, encoding='utf-8').read()

def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)

# ---- 1. タイトルと viewport ----
#   ★viewport は C10_page.html には書かれていません。
#     GAS の doGet が .addMetaTag('viewport', ...) で後から足していました。
#     静的ページには足してくれる人がいないので、ここで書きます。
#     無いと、スマホがページを幅980pxとみなして全体を縮小表示します
#     （＝「小さくなった」「左右に余白ができた」の正体）。
rep('<title><?!= pageTitle ?></title>',
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<title>ご注文内容のご確認とご承認</title>')

# ---- 2. 読み込み中の表示（MODELが届くまでの数百ミリ秒） ----
rep("""<div class="wrap">

  <!-- ============ ご確認画面 ============ -->""",
"""<div class="wrap">

  <!-- ============ 読み込み中（静的ホスティング版だけにあります）============
       旧方式はサーバーがMODELを埋めてHTMLを返すため、この状態がありませんでした。
       静的ページは、開いてからMODELを取りに行くので、その間だけこれを出します。 -->
  <div id="screenLoading" class="card" style="text-align:center;padding:44px 16px;">
    <span class="spinner"></span> 読み込んでいます…
  </div>

  <!-- ============ ご確認画面 ============ -->""")

# ---- 3. MODEL の埋め込み → 通信の作法＋google.script.run の受け皿 ----
rep("""<script>
  var MODEL = <?!= modelJson ?>;
</script>""",
"""<script>
/* ====================================================================
   静的ホスティング版（Android の /u/2 対策）
   ★ここだけ、お客様向けWebAppの /exec URL に書き換えてください。
   ==================================================================== */
var GAS_API = 'https://script.google.com/macros/s/AKfycbw5C6BZI5BOznnZvZ49DphNg1fLCQm40zv6KO7nbyesjkSrqYi5FBTmCZl-tyRDuSlWLQ/exec';

/* URLの ?t=（トークン） */
var TOKEN = (function () {
  var q = new URLSearchParams(location.search);
  return q.get('t') || q.get('token') || '';
})();

/* MODEL は、開いたあとサーバーから受け取ります（旧方式は埋め込みでした） */
var MODEL = null;

/* ====================================================================
   通信の作法　★変更しないでください
   （GTNET自動車保険システム 2026-09-10 の回答書 §6-2 のまま）

   ・別ドメインからの fetch は Cookie を送らない
     ＝ Google が匿名として扱う ＝ URLに /u/N/ が付かない。
     これが Android 問題の回避そのものです。
   ・credentials は既定のまま。'include' を付けると Cookie が送られ、
     /u/N/ 問題が復活します。
   ・POST の Content-Type は text/plain。application/json にすると
     ブラウザがプリフライト（OPTIONS）を飛ばしますが、GASウェブアプリは
     OPTIONS に応答できないため、必ず失敗します。
     中身が JSON でも、名乗りは text/plain ── これが定石です。
   ==================================================================== */
function apiGet(params) {
  var qs = Object.keys(params).map(function (k) {
    return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
  }).join('&');
  return fetch(GAS_API + '?' + qs, { method: 'GET' }).then(function (r) { return r.json(); });
}
function apiPost(payload) {
  return fetch(GAS_API, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=utf-8' },
    body: JSON.stringify(payload)
  }).then(function (r) { return r.json(); });
}

/* ====================================================================
   google.script.run の受け皿

   【なぜ、わざと同じ形を残すのか】
   この下の画面のコードは C10_page.html とまったく同じです。
   通信の呼び方まで同じにしておけば、画面を直したときに
   「片方だけ直してしまう」事故が起きません。差分は、このファイルの
   頭とお尻だけに閉じ込めてあります。

   ★旧方式（C10_page.html）を撤去したら、この受け皿は残したままで構いません。
     消すと画面のコードを全部書き換えることになります。
   ==================================================================== */
var google = {
  script: {
    run: (function () {
      function make(onOk, onNg) {
        var api = {
          withSuccessHandler: function (fn) { return make(fn, onNg); },
          withFailureHandler: function (fn) { return make(onOk, fn); }
        };
        function bind(name, call) {
          api[name] = function () {
            var args = Array.prototype.slice.call(arguments);
            call(args)
              .then(function (res) { if (onOk) { onOk(res); } })
              ['catch'](function (e) { console.error(e); if (onNg) { onNg(e); } });
          };
        }
        bind('getOrderPdf',   function (a) { return apiGet({ api: 'orderPdf', t: a[0] }); });
        bind('getTermsPdf',   function (a) { return apiGet({ api: 'termsPdf', t: a[0] }); });
        bind('markTermsRead', function (a) { return apiPost({ action: 'markRead', token: a[0], kind: a[1] }); });
        bind('submitSign',    function (a) { return apiPost({ action: 'sign',     token: a[0], payload: a[1] }); });
        return api;
      }
      return make(null, null);
    })()
  }
};
</script>""")

# ---- 4. 即実行 → 名前のある関数に（MODELが届いてから呼ぶ） ----
rep("""<script>
(function () {
  'use strict';
""",
"""<script>
/* ★旧方式はここが即実行でした。静的版は MODEL を受け取ってから呼びます。
   中身は C10_page.html と1行も違いません。 */
function bootPage() {
  'use strict';
""")

# ---- 5. 末尾：起動処理を足す ----
rep("""
})();
</script>

</body>""",
"""
}

/* ====================================================================
   起動
   ★bootstrap（読み取り）ではトークンを消費しません。
     お客様が何度リロードされても、署名できなくなることはありません。
   ==================================================================== */
(function start() {
  if (!TOKEN) {
    bootError('リンクが正しくありません。\\nお手数ですが、担当までご連絡ください。');
    return;
  }
  apiGet({ api: 'bootstrap', t: TOKEN })
    .then(function (res) {
      if (!res || !res.ok || !res.model) {
        bootError((res && res.message) ? res.message :
          'システムの都合により、ただいま画面を表示できません。\\n' +
          'お手数ですが、しばらく時間をおいてからもう一度お試しください。');
        return;
      }
      MODEL = res.model;
      hideLoading();
      bootPage();
    })['catch'](function (e) {
      console.error(e);
      bootError('通信に失敗しました。\\n電波の良い場所で、もう一度お試しください。');
    });
})();

function hideLoading() {
  var el = document.getElementById('screenLoading');
  if (el) { el.classList.add('hide'); }
}

/** MODEL を受け取る前に失敗したときの画面（受け取った後のエラーは bootPage 側が出します） */
function bootError(message) {
  var g = function (id) { return document.getElementById(id); };
  hideLoading();
  if (g('hCompany')) { g('hCompany').textContent = 'GTNET株式会社'; }
  if (g('dMark'))    { g('dMark').textContent = '🔒'; }
  if (g('dTitle'))   { g('dTitle').textContent = '画面を表示できませんでした'; }
  if (g('dMsg'))     { g('dMsg').textContent = message; }
  if (g('dContact')) { g('dContact').classList.remove('hide'); }
  if (g('screenDone')){ g('screenDone').classList.remove('hide'); }
  window.scrollTo(0, 0);
}
</script>

</body>""")

io.open(DST, 'w', encoding='utf-8', newline='').write(s)
print('生成しました: %d bytes' % len(s))
