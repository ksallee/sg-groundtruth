---
tags: [write, version, create, entity-field]
verdict: see below
---

# 012_create_version

**Endpoint** `POST /api/v1/entity/versions`

**Docs claim** Versions need a project; entity links are written as {type, id}.

**Actual**

```
sandbox project id: 1180
Version mandatory fields: ['code']
POST /entity/shots -> 201
shot id: 7444
  201 minimal (project + code): id=26262 rels=['created_by', 'cuts', 'notes', 'open_notes', 'playlists', 'project', 'published_files', 'sg_deliveries', 'tags', 'tasks', 'updated_by', 'user']
  201 with entity link: id=26263 rels=['created_by', 'cuts', 'entity', 'notes', 'open_notes', 'playlists', 'project', 'published_files', 'sg_deliveries', 'tags', 'tasks', 'updated_by', 'user']
  400 entity as bare id (no type): null
  400 no project at all: null
```

**Verdict** see below
