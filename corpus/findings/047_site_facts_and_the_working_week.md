---
tags: [discovery, silent, user, date, error-handling]
endpoints: [GET /license_info, GET /subscription_seat/user_subscriptions, GET /schedule/work_day_rules, PUT /schedule/work_day_rules, POST /subscription_seat/user_subscriptions, PUT /preferences/update]
phase: schema
scope: api
measured: sample project 1 of 1, plus site-wide windows of 14 and 730 days
verdict: Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.
---

# 047_site_facts_and_the_working_week

**Q** What does the site tell you about itself beyond `/preferences`, and which of it is writable?

**Endpoint** `GET /license_info ; GET /subscription_seat/user_subscriptions ; GET /schedule/work_day_rules ; PUT /schedule/work_day_rules ; POST /subscription_seat/user_subscriptions ; PUT /preferences/update`

**Docs claim** `/spec.json` lists all six. Its `/license_info` example gives the counts as strings, and
its `work_day_rules` example gives a `links.self` under `/api/v1.1/`.

**Actual**

```
=== three site-fact calls, three envelopes
GET /license_info      {"data": {...}, "status": "success"}      no links
  {"assigned": 4, "rule": "quantity", "free": 46, "total": 50, "type": "license-count"}
  integers, not the strings /spec.json shows. rule=unlimited is what makes free -1
GET /subscription_seat/user_subscriptions   {"<id>": "not_for_resale", "<id>": null, ...}
  bare hash, no data and no links. keys are strings. 14 keys
GET /schedule/work_day_rules   {"data": [...], "links": {"self": "/api/v1/..."}}   v1, not v1.1

=== the three counts of "how many users" do not reconcile
license_info.assigned 4    seat-hash keys 14    HumanUser rows 24
sg_status_list x seat hash: act {in hash 5, absent 1}, dis {in hash 9, absent 9}

=== work_day_rules answers 200 for a scope that is not there
?start_date=2026-03-02&end_date=2026-03-15                 -> 200, 14 rows, STUDIO_WORK_WEEK
  Mon..Fri working=true, Sat/Sun false; 730-day window -> 730 rows, no links.next
&project_id=999999999 / &user_id=999999999                 -> 200, the studio default
?start_date=2026-03-02                -> 400 {"end_date": ["end_date is missing"]}
?start_date=2026-03-15&end_date=2026-03-02
  -> 400 "start_date_and_end_date 'end_date' must be greater than or equal to 'start_date'"
?start_date=03/02/2026                -> 400 {"status": "error", "error": "invalid date"}  no errors[]

=== the write side, rejections only
PUT  /schedule/work_day_rules {}      -> 400 {"date": ["date is missing"], "working": ["working is missing"]}
  {"date": "not-a-date", "working": true, "recalculate_field": "definitely_not_a_field"}
  -> 400 "recalculate_field invalid value. The valid values are 'duration' or 'due_date'"
POST /subscription_seat/user_subscriptions {}                  -> 200 {}
  {"999999999": "definitely_not_a_subscription"}  -> 400 "Invalid humanUserId 999999999"
  [{...}]                                         -> 400 "Invalid JSON body. Expected Hash but received Array."
PUT  /preferences/update  all six bodies, {} through complete
  -> 400 code 111 "Updating the preferences is not available", source null, 170 bytes every time
```

**Teaches**

- **Every site-fact call has its own envelope.** `/license_info` returns `{data, status}` with no
  `links`, the subscription hash returns neither, and only `/schedule/work_day_rules` is JSON:API.
  One decoder does not read all three.
- **A `project_id` or `user_id` that does not exist is a 200, not a 404.** The studio default answers
  instead, and `reason` reads `STUDIO_WORK_WEEK` for both the fallback and a real studio-wide answer.
  A client asking "is this a working day for project X" gets a plausible answer for a project that
  is not there. Check the id first.
- One endpoint, two error shapes. A missing or out-of-order parameter is a JSON:API `errors` array;
  an unparseable date is `{"status": "error", "error": "invalid date"}` with no `errors` key.
  `r.json()["errors"][0]` raises on the second.
- No paging on `work_day_rules`: a 730-day window returned 730 rows in one 61631-byte response, with
  no `page` envelope and no `links.next`. Bound the range in the request.
- `PUT /preferences/update` refused every body identically on the probed site, `{}` and a complete one
  alike, so the 400 tells a client nothing about its own payload and the parameter names in
  `/spec.json` stay unverified. The code is 111 and `source` is `null`, not the 103 with a populated
  `source` that parameter errors use elsewhere.
- The three ways to count users disagree. On the probed site `license_info.assigned` was 4, the
  subscription hash held 14 keys and there were 24 HumanUser rows, and `sg_status_list` did not
  predict which users the hash held. Do not derive a seat count from a user query.
- `POST /subscription_seat/user_subscriptions` with `{}` answers 200 with `{}`: a 200 that assigned
  nothing looks exactly like one that assigned something. Its per-user failures are a 207 whose
  messages are strings inside the hash, which `r.ok` passes over.
- The write paths for the working week, subscriptions and custom entity slots were exercised only
  with bodies that must fail. Each of the three changes configuration for every user of the site, and
  none has a dry run.
