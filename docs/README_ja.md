# 🐞 NoteBug — 日本語マニュアル

[← README に戻る](../README.md)

PyCharm風のブレークポイント・デバッガを、Google Colab / Jupyter の中で使える教育用ツールです。
PyCharm-style breakpoint debugger for teaching Python in Google Colab / Jupyter.

- 行番号クリックでブレークポイント、`# bp` や `breakpoint()` で事前設定
- 実行/再開・ステップオーバー・ステップイン・ステップアウト・**1ステップ戻る**
- 変数（変化はオレンジ、新規は new）、コールスタック、インライン値、出力
- 止まった時点のフレームで式やコードを試せるコンソール（Colab）。`for` / `if` など複数行も可
- テーマ 4 種（night / light / darcula / contrast）と文字サイズ変更、色の個別上書き
- numpy / pandas / matplotlib 対応（DataFrame の表プレビュー、グラフを出力欄に表示）
- ペット、⚡パワーモード、効果音、🏆実績　／　韓国語・日本語・英語

## インストール / Install

```bash
pip install git+https://github.com/aki5413/notebug   # GitHub から（いちばん手軽）
pip install notebug                                  # PyPI に公開した後
pip install -e ".[test]"                              # このフォルダから（開発用）
```

Colab / Jupyter のセルでは `%pip install ...` と書きます（`!pip` でも Colab では動きますが、`%pip` は必ず実行中のカーネルに入ります）。

## 使い方 / Usage

```python
import notebug                      # これで %%notebug が使えるようになる
notebug.config(lang="ko", theme="light", font_size=16)   # ノート全体の既定値（任意）
```

```python
%%notebug --pet dog --power
total = 0
for i in range(5):
    total += i      # bp
print(total)
```

| API | 内容 |
|---|---|
| `%%notebug [options]` | セルをデバッガで実行 |
| `notebug.run(code, namespace=globals())` | 文字列のコードをデバッグ |
| `notebug.run_file("hw1.py")` | .py ファイルをデバッグ |
| `notebug.save_html(code, "demo.html")` | ブラウザだけで開ける HTML を保存 |
| `notebug.config(**options)` | 既定値の設定（`reset=True` で初期化） |
| `python -m notebug hw1.py -o hw1.html` | コマンドラインから HTML を作成 |

オプション（マジックでは `--lang ko` のように指定）:

| option | 値 | 既定 |
|---|---|---|
| `lang` | `ko` / `ja` / `en` | ブラウザで最後に選んだ言語 |
| `pet` | `cat` `dog` `hedgehog` `penguin` `turtle` `dino` または任意の絵文字 | `cat` |
| `power` / `sound` | パワーモード / 効果音（`--no-power` で強制オフ） | 前回の設定 |
| `achievements` | 🏆 実績の表示（`--no-achievements`） | `True` |
| `theme` | `night` / `light` / `darcula` / `contrast`（`--theme light`） | 前回の設定、なければ `night` |
| `font_size` | コードの文字サイズ px、9〜28。画面全体がこれに合わせて拡大縮小（`--font 16`） | 前回の設定、なければ 13 |
| `colors` | 個別の色の上書き（下記）。`config` / `run` のみ | なし |
| `max_steps` | 記録する最大ステップ数（`--max`） | 3000 |
| `export` | 実行後の変数をノートブックに戻す（`--no-export`） | `True` |

## コンソール / Console

| キー | 動作 |
|---|---|
| Enter | 1 行なら実行。`:` で終わる行のあとは自動で字下げして次の行へ |
| 空行で Enter | 複数行のコードを実行（Python の対話モードと同じ） |
| Shift+Enter | いつでも改行 |
| Ctrl+Enter（Mac は ⌘+Enter）/ ▶実行 | いつでもすぐ実行 |
| Tab / Shift+Tab | 字下げ / 字下げを戻す |
| ↑ / ↓ | 前の入力を呼び出す（複数行ごと） |

最後の行が式なら、その値が表示されます（`for` で合計してから `total` と書くなど）。
日本語・韓国語の変換確定の Enter では実行されません。

## データ分析のコード / numpy · pandas · matplotlib

- **変数欄**: `DataFrame 1000×3`・`Series (4,) float64`・`ndarray (3, 4) int64` のように形と型を表示。▸ で展開すると
  DataFrame は先頭 8 行 × 8 列の表、Series / ndarray は要素の一覧。中身が変わるとオレンジで表示（2000 行以下）。
- **グラフ**: `plt.show()`・`display(fig)`・セル末尾に残った図は、ノートブックの外ではなくデバッガの**出力欄**に、
  そのステップの時点で表示されます（クリックで拡大）。コンソールで `plt.plot(...)` と書いた図も表示されます。
- **ノートブックと同じ動き**: 最後の行の式（`df.head()` など）の値と `display(...)` の内容を出力欄に表示。
  `%matplotlib inline` や `!pip install ...` のようなマジックもそのまま書けます（`%%notebug` セル）。
- **ライブラリから呼ばれる関数には入らない**: `df.apply(lambda ...)`・`np.vectorize(f)` などに渡した関数は
  1 ステップとして実行されます（行数分のステップで記録が埋まらないように）。`sorted(key=...)`・`map(f, ...)` など、
  自分のコードから直接呼ぶ関数には従来どおりステップインできます。
- **長い処理**: `max_steps` を超えると記録だけ止めて、プログラムは最後まで実行します（最後の変数・出力・グラフは正しく表示）。
  記録停止後 10 秒たっても終わらない場合は無限ループとみなして止めます。

注意: コンソールはその時点までプログラムを**再実行**して評価します。ファイルの読み込みや重い計算も再実行されるため、
大きなデータでは 1 回の入力に数秒かかることがあります。`np.random.seed(...)` を使わない乱数（`np.random.default_rng()` など）は、
再実行で値が変わることがあります。

## 色の個別上書き / Custom colours

`colors` に CSS 変数名（`--` なし）と色を渡します。テーマを選んだうえで一部だけ変えられます。

```python
notebug.config(theme="light", colors={"cur": "rgba(0,160,255,.25)", "kw": "#0000cc"})
```

主な名前: `bg`（背景）, `panel`, `text`, `dim`, `line`（枠線）, `cur`（現在行）, `bpline`（ブレークポイント行）,
`ret`, `exc`, `kw`（キーワード）, `str`（文字列）, `num`（数値）, `com`（コメント）, `bi`（組み込み関数）, `fn`（関数名）,
`amber`（変更された値・▶）, `mint`（new）, `coral`（エラー・ブレークポイント）, `sky`（変数名）, `violet`（インライン値）。
全一覧は `src/notebug/assets/ui.css` の先頭にあります。

## 仕組み / How it works

1. `sys.settrace` でプログラムを最後まで実行し、1 行ごとの変数・出力を記録します（`tracer.py`）。
2. 記録を HTML/JS の画面に埋め込んで表示します（`render.py`, `assets/`）。ステップ移動や「戻る」はブラウザ内で完結します。
3. コンソールの入力は Colab のコールバックで Python に送られ、その時点まで**再実行**してから、そのフレームの中で評価されます。`input()` の値と乱数の状態は記録して再現します。

## ファイル構成 / Layout

```
src/notebug/
  __init__.py     公開 API（import 時に %%notebug を登録）
  core.py         config / run / run_file / to_html / save_html
  tracer.py       記録（record）と再実行評価（eval_at）
  encoding.py     値を画面用の小さな JSON に変換
  render.py       assets を組み立てて HTML にする
  ipython.py      %%notebug マジックと Colab コールバック
  __main__.py     python -m notebug
  assets/
    ui.html  ui.css  ui.js   画面
    i18n.js                  画面の文言（ko / ja / en）
tests/test_notebug.py       python -m pytest tests
```

画面の文言を直したいときは `assets/i18n.js`、見た目は `assets/ui.css` だけを編集すれば済みます。

## 制限 / Limitations

- コンソールは Colab でのみ動作します（Jupyter / 保存した HTML では変数パネル・ステップ実行のみ）。
- 時刻・ファイル・ネットワークに依存するコードは、コンソール用の再実行で結果が変わることがあります。
- 記録は `max_steps` で止まります（プログラム自体は最後まで実行され、最後の状態は表示されます）。それ以降の途中経過はステップで見られません。
