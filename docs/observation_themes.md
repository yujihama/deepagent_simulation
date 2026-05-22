# 観察テーマ設計

## 目的

このMVPの最初の題材は申請承認ですが、将来的には値引き、契約レビュー、経費精算、取引先対応などへ観察対象を差し替えられるようにします。そのため、UIとAPIは「申請一覧」へ直接依存せず、観察テーマごとの「業務レコード」を表示する構造に寄せています。

## 現在の構成

現在有効なテーマは `application_approval` です。

| 項目 | 値 |
| --- | --- |
| 表示名 | 申請承認 |
| recordType | approval_request |
| source | applications |
| 表示フィールド | 相手先、内容、金額、必要承認、指定承認、状態 |
| シナリオ | 正常申請、高額一括、分割誘発、急ぎ依頼、複数比較 |

内部DBには既存の `applications` テーブルを残し、`GET /api/business-records` がこれを業務レコードへ変換して返します。これにより、現在の申請承認シナリオを壊さずに、画面側はより汎用的なレコード表示へ移行できます。

## API

### GET /api/observation-themes

利用可能な観察テーマ一覧と現在の有効テーマを返します。

```json
{
  "activeThemeId": "application_approval",
  "themes": [
    {
      "id": "application_approval",
      "name": "申請承認",
      "enabled": true,
      "recordType": "approval_request",
      "recordLabel": "申請",
      "recordPluralLabel": "業務レコード",
      "source": "applications",
      "tableColumns": [
        { "key": "customer", "label": "相手先" },
        { "key": "purpose", "label": "内容" },
        { "key": "amount", "label": "金額" }
      ]
    }
  ]
}
```

### PUT /api/observation-theme

有効テーマを切り替えます。現時点では `application_approval` のみ有効で、他テーマはテンプレートとして表示だけします。

```json
{ "themeId": "application_approval" }
```

### GET /api/business-records

現在の観察テーマに応じた業務レコードを返します。初期表示では過去runのレコードを混ぜず、`runId` 指定時だけ対象runのレコードを返します。

```json
[
  {
    "id": "app-...",
    "runId": "run-...",
    "themeId": "application_approval",
    "recordType": "approval_request",
    "title": "展示会ブース関連の手配",
    "ownerAgent": "sales-a",
    "counterparty": "取引先A",
    "status": "承認済み",
    "fieldValues": {
      "customer": "取引先A",
      "purpose": "展示会ブース関連の手配",
      "amount": "800,000円",
      "approvalRequiredRole": "営業課長",
      "requestedApprover": "営業課長",
      "status": "承認済み"
    }
  }
]
```

## 新しい題材を追加する手順

1. `backend/domain_config.py` に観察テーマを追加する。
2. 必要な業務レコードの保存先を追加する。申請承認のように既存テーブルを変換しても、将来は汎用 `business_records` テーブルを追加してもよい。
3. `GET /api/business-records` にテーマ別の変換処理を追加する。
4. 初期ドキュメントを追加する。例: 値引き規定、契約レビュー仕様書、経費精算マニュアル。
5. シナリオ初動指示を追加する。ランナーは行動を固定せず、初期条件と背景だけを投入する。
6. 必要なtoolを定義する。例: `submit_discount_request`, `submit_contract_review`, `submit_expense_claim`。
7. 監査Agentの観点ドキュメントと事後評価ロジックを追加する。

## ドメインパック案

将来は観察テーマ、初期agent、ドキュメント、シナリオ、tool定義、監査観点を1つのパックとして読み込めるようにします。

```json
{
  "theme": {
    "id": "discount_approval",
    "name": "値引き承認",
    "recordType": "discount_request",
    "recordPluralLabel": "業務レコード",
    "tableColumns": [
      { "key": "customer", "label": "相手先" },
      { "key": "deal", "label": "案件" },
      { "key": "discountRate", "label": "値引率" },
      { "key": "reviewer", "label": "審査者" },
      { "key": "status", "label": "状態" }
    ]
  },
  "documents": [
    { "id": "discount-policy", "title": "値引き承認規定", "category": "規定" }
  ],
  "tools": ["send_message", "submit_discount_request", "read_documents"],
  "auditFocus": ["承認権限回避", "名目変更", "個人的便宜"]
}
```

## 設計上の制約

- ERP Agentや監査Agentの責務分離は題材が変わっても維持します。業務処理agentは届いたレコードを仕様書に従って処理し、監査Agentは完了後に逸脱を評価します。
- agentの独立性とrun内コンテキスト保持は題材に依存させません。
- モック実行は画面とAPI確認用です。自然な判断観察にはLive DeepAgent実行を使います。
