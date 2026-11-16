# Easy i18n Skill — らくに多言語対応

多言語対応を「最もらくに、効果的に、効率よく」行うための AI エージェント向けスキルです。2025〜2026年のライブラリと翻訳道具を横断調査した結論をもとに設計しています。

> **The one default:** Keep ONE semantic-key, ICU-MessageFormat catalog in git (`messages/en.json` as the source of truth), translate only the diff with an LLM CLI, and let each platform's native, type-safe runtime consume a generated copy. No paid TMS by default. Typical solo cost: $0–$5 per language, $0/month tooling.

## 結論（このスキルが教える方法）

| 場面 | 既定の方法 |
|---|---|
| 正本 | 意味キー＋ICU の中央 JSON カタログ1つ（単一プラットフォームならその標準ファイル自体が正本） |
| Next.js | next-intl（ICU 内蔵） |
| Vite + React（新規） | Paraglide JS（コンパイラ方式、型安全）／ 汎用性重視なら react-i18next + i18next-cli |
| Android | 標準リソース `strings.xml` + `stringResource()`（サードパーティ不要） |
| Chrome 拡張 | `chrome.i18n` + `_locales`（マニフェスト翻訳に必須） |
| 翻訳 | LLM の CLI で差分だけ翻訳＋用語集＋文脈メモ。大事な約20文だけ人が確認 |
| 検証 | キー・プレースホルダ一致の機械検証＋擬似ロケール＋プラットフォーム標準の厳格チェック |

やらないこと：文字列の連結、コードでの複数形判定、日付・金額の手整形、MessageFormat 2 の先行採用、個人開発での有料 TMS 前提。

## スキル構成

`skills/easy_i18n/`

- `SKILL.md` — 本体（絶対のルール、方式判定、カタログ、翻訳、配布、検証、ストア掲載文）
- `references/` — 判断表、ICU チートシート、プラットフォーム別ガイド、翻訳ワークフロー、落とし穴と確認リスト、ストア掲載文
- `scripts/` — 動作検証済みの道具
  - `validate_locales.py` — 全ロケールのキー集合・プレースホルダ集合・空訳を検証（失敗で exit 1）
  - `pseudo_localize.py` — 擬似ロケール生成（長さ +35%、アクセント付き）
  - `convert_catalog.py` — 中央 JSON → Android `strings.xml` / Chrome `_locales` 変換（ICU 複数形は警告を出す）
- `templates/` — カタログ雛形（en / ja）、用語集、ストア掲載文

## インストール

このリポジトリを取得し、`skills/easy_i18n/` フォルダをスキルディレクトリへコピーしてください。

- Codex の場合は通常 `~/.codex/skills/` へコピーします。`SKILL.md` 冒頭の frontmatter（name / description）が登録情報になります。
- Muse の場合は `~/workspace/custom-skills/` へコピーし、メタデータは同梱の考え方に沿って `skill.yaml` を置きます（本文は同一）。

## 使い方

対象アプリとプラットフォーム、追加したい言語を添えて依頼します。

> `$easy_i18n` を使って、このアプリを英語とスペイン語に対応させて。

> この Chrome 拡張の多言語対応を点検して。未訳とプレースホルダ崩れがないか検証して。

## 調査について

方式選定の根拠（ライブラリ比較、CLDR 複数形、翻訳コスト、TMS 価格、ストア掲載文の分離など）は 2026-11-16 時点の公開資料に基づきます。ライブラリの版と価格は変わるため、スキル本体では「採用前に公式で現行版を確認する」ことをルールにしています。ダウンロード数などの絶対値は出典で大きくぶれるため、順位と幅で判断しています。

## 状態

- 現在の版は 0.1.0 です。スクリプト3点はサンプルカタログで動作検証済み（正常系の一致、欠けキーとプレースホルダ不一致の検出、Android / Chrome への変換と ICU 警告）。
- 実アプリへの適用実走はこれからです。詰まった点はスキルへ還元します。

## ライセンス

MIT License
