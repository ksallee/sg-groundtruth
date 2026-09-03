---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Delivery
verdict: On this site Delivery has 11 sg_ fields and 3 vocabularies over 0 rows. The codes here are what the API stores; the labels are editable.
---
# Delivery

What this site configures on top of the shipped `Delivery` card. The card above is the API layer; everything here is one site's own.

0 rows site-wide, across every project.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_contents` | text | yes | Contents |
| `sg_delivery_method` | list | yes | Delivery Method |
| `sg_delivery_progress` | list | yes | Delivery Progress |
| `sg_delivery_type` | list | yes | Type |
| `sg_due_date` | date | yes | Due Date |
| `sg_from` | entity | yes | From |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_received_date` | date | yes | Received Date |
| `sg_status_list` | status_list | yes | Status |
| `sg_upload_url` | url | yes | Upload URL |
| `sg_versions` | multi_entity | yes | Version <-> Link |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_delivery_method` | list | 4 | `FTP`, `Aspera`, `FedEx`, `Sneaker Net` |  |
| `sg_delivery_progress` | list | 11 | `In transit`, `Delivery cancelled`, `Delivery failed`, `Delivered`, `Ingesting`, `Ingest cancelled`, `Ingest failed`, `Ingest suspended`, `Received`, `Received with warnings`, `Transcode cancelled` |  |
| `sg_status_list` | status_list | 4 | `opn (Open)`, `ip (In Progress)`, `dlvr (Delivered)`, `recd (Received)` | opn |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.
