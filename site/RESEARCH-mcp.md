# MCP servers for Flow Production Tracking: verified claims

Verification pass, 2026-09-02. An earlier survey covered nine repositories. This file records only what
was re-read against current source, claim by claim, with the file and lines quoted. Claims not re-read are
listed at the end and marked unverified.

## Method

Each repository was snapshotted from the GitHub tarball of its default-branch HEAD and grepped locally.
No clone, no fork, no contact. The extracted file count matched the untruncated recursive git tree for
each repository, so the snapshot is the complete tree at that commit: 111 files, 13 files, 175 files.

| repository | default branch | HEAD | HEAD commit date | licence | stars |
|---|---|---|---|---|---|
| `abrahamADSK/fpt-mcp` | `main` | `45aa77e` | 2026-08-16 | MIT | 1 |
| `rfletchr/ShotgunMcpGo` | `master` | `ef0f127` | 2026-06-06 | MIT | 6 |
| `loonghao/shotgrid-mcp-server` | `main` | `6652a6a` | 2026-05-19 | MIT | 64 |

`loonghao/shotgrid-mcp-server` reports `pushed_at` 2026-07-20 from branches other than `main`; the last
commit on `main` is 2026-05-19. Its latest release is `v0.15.4`, published 2026-01-28.

No claim below has CHANGED since the survey. Eight of eight are CONFIRMED.

---

## 1. abrahamADSK/fpt-mcp

Python, wraps `shotgun_api3`. It issues no REST calls of its own: the only `api/v1` string in the package
is inside a docstring at `src/fpt_mcp/rag/search.py:192`. `src/fpt_mcp/docs/REST_API.md` is RAG content,
indexed by `src/fpt_mcp/rag/build_index.py` and retrieved into the model's context by `search_sg_docs`.
What the document says is what the model is told.

### 1a. Instructs following `links.next` until null. CONFIRMED

`src/fpt_mcp/docs/REST_API.md`, three prose statements and one code example.

    776: Follow `links.next` until it's null (end of results).
    785: | **Iteration** | Single call or loop with page increment | Follow `links.next` |
    1390: | **Iteration** | Loop incrementing `page` | Follow `links.next` in response |

Line 776 closes the Cursor-Based Pagination section. Lines 785 and 1390 are the REST column of two
Python-SDK-versus-REST comparison tables. The code example at 1526-1540, labelled **RIGHT**, is the same
instruction as executable Python:

    while True:
        response = requests.get(
            f"/api/v1/entity/assets?page[size]=500&page[number]={page}",
            headers=headers
        )
        data = response.json()["data"]
        all_assets.extend(data)
        if not response.json()["links"].get("next"):
            break
        page += 1

Finding 006 measured 31 pages of which 30 were empty, every one carrying `links.next`. The loop's only
exit condition is never reached.

### 1b. States all requests require `Content-Type: application/json`. CONFIRMED

`src/fpt_mcp/docs/REST_API.md:112-120`:

    ### Required Headers

    All REST API requests require:

    ```
    Authorization: Bearer {access_token}
    Accept: application/json
    Content-Type: application/json
    ```

Findings 004 and 020: `POST /entity/<type>/_search` and `_summarize` reject `application/json` with 415
and require `application/vnd+shotgun.api3_array+json` or `...api3_hash+json`. Neither vendor content type
appears anywhere in the document; `grep -i "vnd+shotgun\|api3_array\|api3_hash"` over all 1602 lines
returns nothing.

Correction to the earlier survey, which said the document's own `_search` example carries the wrong
header. It does not. The Advanced Search via POST section at line 345 shows a request body only, with no
header block. The wrong header reaches `_search` through the blanket statement at line 114, not through
that example.

The `_search` body shown at 350-378 is `{"field", "operator", "values"}` objects plus
`"filter_operator": "and"`. Finding 004 measured that shape as 400 `Missing logical operator`. This was
not among the claims to verify; it is recorded here because it was read in passing.

### 1c. Hardcodes status codes as a regular expression. CONFIRMED

`src/fpt_mcp/safety.py:121`, one entry in the `_DANGEROUS_PATTERNS` list:

    r'"sg_status_list"\s*:\s*"(?!(?:ip|wtg|cmpt|hld|fin|omt|rev|kik|apr|na|rdy)")[a-z_]+"',

Eleven codes. `check_dangerous` (line 148) runs every pattern with `re.search` and returns a formatted
string; `shotgrid.py` calls it before `sg_find`, `sg_create`, `sg_update`, `sg_delete` and `sg_batch`. It
warns, it does not block, and the warning text is prepended to the tool result.

Two qualifiers. The entry's own remedy text ends "Run sg_schema on the entity to confirm legal status
codes for your project, custom pipelines may add or remove codes", so the module is aware the list is not
authoritative. And the regex is a negative lookahead: it fires only on a status that is *not* in the list.
A studio with a custom code gets a false warning. A code the project hides via `hidden_values` is not in
the list either, so it also trips the warning, but for the wrong reason and with the wrong remedy, and
REST will write it regardless (`field_types/status_list`).

---

## 2. rfletchr/ShotgunMcpGo

Go, 950 lines in `main.go`, one Go source file plus `cmd/fetchdocs/main.go`. Built on
`github.com/rfletchr/ShotgunGo v0.1.0`, the same author's REST client, so it talks to the REST API
directly.

### 2a. Ships per-`data_type` tables of operators, value shapes and summarize behaviour. CONFIRMED

Three package-level maps in `main.go`, under the comment `// Static reference data`:

| table | line | keys | served by |
|---|---|---|---|
| `operatorsByType` | 194 | 17 | `sg_operators` |
| `dataTypes` | 214 | 22 | `sg_data_types` |
| `summarizeTypes` | 244 | 16 | `sg_summarize_types` |

A fourth map, `operatorArgs` (line 163), gives the value shape each operator name takes. `sg_operators`
joins the two: for a known type it returns `{operator: argument shape}`.

Against our matrix, the specific gaps:

`operatorsByType` has no entry for `color`, `footage`, `password`, `serializable` or `url`, though all
five are keys in `dataTypes`. `handleOperators` (line 647) answers an unknown key with

    "unknown or unsupported field type %q — filterable types: %s"

`field_types/password`, `serializable` and `url` record that those three accept no relation at all, so
the message is right by accident. `field_types/color` records four accepted relations, `is`, `is_not`,
`in`, `not_in`, byte-identical to `list` and `status_list`, with the server's own `Valid relations` list
in the recorded 400. For `color` the message is wrong. The three types our matrix covers that are absent
from both maps, `summary`, `calculated` and `pivot_column`, also return the "unknown or unsupported"
message, and each 400s with a different error string.

`dataTypes["date_time"]` reads `"notes": "Stored as UTC. API auto-converts to/from client local time."`
That is `shotgun_api3` behaviour. `field_types/date_time`: over REST the value reads and writes as
`YYYY-MM-DDTHH:MM:SSZ`, a written offset is silently normalised, a zoneless string is taken as UTC, and a
date-only filter value means midnight UTC.

`dataTypes["float"]` reads `{"value": "float | null", "range": "-999999999.999999 to 999999999.999999"}`.
`field_types/float`: the value reads back as a JSON string, not a number, and an Integer is rejected on
both write and filter with `expected [String, BigDecimal, Float, NilClass] data type(s) but got
Integer: 1`. Neither is stated.

`dataTypes["multi_entity"]` gives `{"value": "list", "structure": "[{\"type\": string, \"id\": int}, ...]"}`
and nothing about a bare list replacing the whole link set.

`dataTypes["status_list"]` is `{"value": "string | null"}`.

### 2b. Returns `has_next` taken directly from the presence of `links.next`. CONFIRMED

`main.go:470` in `handleFind` and `main.go:589` in `handleTextSearch`:

    out := map[string]any{
        "data":     results,
        "has_next": page.HasNext(),
        "has_prev": page.HasPrev(),
    }

`ShotgunGo` at tag `v0.1.0`, `page.go`:

    // HasNext reports whether there is a subsequent page of results.
    func (p *Page) HasNext() bool {
        return p.links.Next != ""
    }

Finding 006: `links.next` is emitted on every page including empty ones, so `has_next` is `true` on the
last page of every query.

The library's own iterator does not have the bug. `ShotgunGo/query.go`, `Iter`:

    if !page.HasNext() || len(page.Entities) == 0 {
        return
    }

The `len(page.Entities) == 0` guard terminates it. Only the value the MCP layer reports to the model is
affected.

---

## 3. loonghao/shotgrid-mcp-server

Python on FastMCP, wraps `shotgun_api3`. The REST transport findings do not reach it; the field semantics
do.

### 3a. Serves status choices without subtracting `hidden_values`. CONFIRMED

`src/shotgrid_mcp_server/schema_resources.py:24-50`, the whole of `_extract_status_choices`:

    properties: Mapping[str, Any] = field_schema.get("properties", {}) or {}

    valid_values = (properties.get("valid_values") or {}).get("value")
    display_values = (properties.get("display_values") or {}).get("value")
    default_value = (properties.get("default_value") or {}).get("value")
    data_type = (field_schema.get("data_type") or {}).get("value")

Four reads, `hidden_values` not among them. `_build_status_payload_for_entity` (line 53) calls
`sg.schema_field_read(entity_type)` with no project argument, so the payload is site-wide, not
project-scoped, and `hidden_values` is per project. The result is registered as the MCP resources
`shotgrid://schema/statuses` and `shotgrid://schema/statuses/{entity_type}`.

The selection is on `data_type == "status_list"` (line 71), which is correct: it does not select fields
by name.

This is the only place in the package that serves status choices. `grep -rn "valid_values"` over
`src/` returns two hits: this file, and a fixture inside a docstring at `tools/read_tools.py:84`.

`field_types/status_list`: a project's usable set is `valid_values` minus `hidden_values`, and REST does
not enforce `hidden_values` itself, so a project-hidden status writes and reads back fine.

### 3b. Published on PyPI. CONFIRMED

`https://pypi.org/pypi/shotgrid-mcp-server/json` returns `shotgrid-mcp-server 0.15.4`, 31 releases,
0.15.4 uploaded 2026-01-28, `Homepage` and `Repository` pointing at `loonghao/shotgrid-mcp-server`.

---

## 4. `hidden_values` appears in none of the three. CONFIRMED

How this was checked. All three default-branch HEAD trees were extracted in full, 299 files total, and
searched with a single case-insensitive regular expression covering the spellings a project might use:

    grep -ria -E "hidden[ _-]?values?" fpt-mcp ShotgunMcpGo shotgrid-mcp-server

Zero matches. The trees are complete, not sampled: the extracted file counts, 111, 13 and 175, match the
`git/trees?recursive=1` blob counts at the same SHAs, and each tree reported `truncated: false`.

Widening to the bare word `hidden`, case-insensitively, gives four matches in three files, none of them
about status visibility:

    fpt-mcp/MODEL_STRATEGY.md:130   KV cache ≈ 2 × layers × seq_len × hidden × bytes_per_elem
    fpt-mcp/MODEL_STRATEGY.md:131   Qwen3.5 9B (28 layers, hidden 3584)
    fpt-mcp/src/fpt_mcp/docs/SG_API.md:1289   - `omt` — Omitted (hidden)
    shotgrid-mcp-server/.../delete_tools.py:115   Retired entities are hidden from most queries by default

Only seven files across the three trees are not text: six `.gif` and one `.png`. Nothing else could hold
a match a grep would miss.

`ShotgunGo v0.1.0`, the Go server's client dependency, was read for `page.go` and `query.go` only, so this
result covers the three servers and not that library.

---

## Name availability, 2026-09-02

Checked, not claimed or reserved.

| name | result |
|---|---|
| `github.com/ksallee/sg-groundtruth` | free. `GET /repos/ksallee/sg-groundtruth` returns 404. GitHub repository search for `sg-groundtruth` returns 0 results across all of GitHub. |
| PyPI `sg-groundtruth` | free. `/pypi/sg-groundtruth/json` returns 404, and `/pypi/sg_groundtruth/json` returns 404. The two normalise to the same project name, so both forms are unclaimed. |
| npm `sg-groundtruth` | free. `registry.npmjs.org/sg-groundtruth` returns 404. |

---

## Not verified in this pass

The earlier survey covered six more repositories and made further claims about the three above. None of
the following was re-read, and none should be published without the same treatment:

- `chordee/mcp-server-shotgrid`, `huikku/shotgrid-mcp`, `dcc-mcp/dcc-mcp-fpt`, `dcc-mcp/fpt-cli`,
  `dffxPipeline/dffx-genai`, and the claim that seven Flow PT MCP servers exist.
- The claim that nothing for Flow PT appears in the official MCP registry, and that Autodesk ships no
  Flow PT MCP server.
- Star counts, commit counts and authorship attributions beyond the table above.
- In `fpt-mcp`: the `filters.py` validator claim, and the claims about the Toolkit and Qt surfaces.
- In `shotgrid-mcp-server`: the `data_types.py` multi_entity claim, the `schema_validator.py` checkbox
  claim, and the absence of a filterability guard.

Two things read in passing during this pass and worth carrying forward:
`fpt-mcp/src/fpt_mcp/rag/build_index.py:169-176` does index any additional `.md` placed in
`src/fpt_mcp/docs/`, so a corpus drop-in needs no code change there.
`ShotgunMcpGo` ships no embedded `.rst` document set; it has `prompts/query_guide.md` and a
`cmd/fetchdocs` command that retrieves docs at build time.
