---
tags: [client, launcher, discovery]
endpoints: [GET /]
phase: protocol
scope: api
measured: site-wide, the configured site's own name and one name no site holds, under three domains, 2026-11-11
coverage: partial
unmeasured: a site created under shotgunstudio.com, and a European-hosted site's hostname. The probed site is neither; blocked on the site
verdict: The probed site answers only at its own host; its name under shotgunstudio.com is 404 HTML, no redirect. Both domains resolve any name, so allowlist the configured host, not a suffix.
---

# 129_hosted_domains

**Q** Under which Autodesk domains does a hosted Flow Production Tracking site answer, and does one
name redirect to another?

**Endpoint** `GET / ; GET /api/v1` on `<name>` under each domain, unauthenticated, redirects not followed

**Docs claim** Autodesk's security ecosystem page (help.autodesk.com, Flow PT Administrator guide,
General security, Ecosystem) lists `<mysite>` under `shotgrid.autodesk.com` and under
`shotgunstudio.com` as the Flow PT hosts, plus `launchdarkly` under the first, `tank` under the
second and `s3-proxy` under both. It names no regional host and says nothing of a redirect. Media
buckets are regional: `sg-media-usor-01`, `-tokyo`, `-ireland`, `-saopaulo`, `-mumbai`, `-sydney`, on
`s3.amazonaws.com` and `s3-accelerate.amazonaws.com`. Autodesk's European data centre beta post
(community forum, 2026-04-22) gives only `mysite-staging` under `shotgrid.autodesk.com` as an
example. All of this is documented, not measured.

**Actual**

```
configured site: <site> under shotgrid.autodesk.com

name      domain                  resolves  GET /                                   GET /api/v1
<site>    shotgrid.autodesk.com   yes       302 -> /user/login?return_path=%2Fmain  200 JSON root document
<unheld>  shotgrid.autodesk.com   yes       404 text/html                           404 text/html
<site>    shotgunstudio.com       yes       404 text/html                           404 text/html
<unheld>  shotgunstudio.com       yes       404 text/html                           404 text/html
<site>    shotgun.autodesk.com    no address
<unheld>  shotgun.autodesk.com    no address

every 404 body begins:
  <!-- This file is used to disable the web server when we are working on the site. -->

GET http://<site host>/  -> 301  location https://<site host>:443/
```

**Teaches**
- On the probed site, the site answers at one host. Its name under `shotgunstudio.com` is not a
  redirect to `shotgrid.autodesk.com`: it is the same 404 a name no site holds gets. Store the host the
  person typed and call that; do not rewrite one domain to the other.
- Both `shotgrid.autodesk.com` and `shotgunstudio.com` resolve any name under them. A proxy that
  forwards to any host matching either suffix forwards to hosts no site serves. Allowlist the
  configured site's exact host.
- A host with no site answers `/api/v1` with `404 text/html`, not JSON. Treat an HTML 404 from
  `GET /api/v1` as "no site at this address" before parsing.
- No name under `shotgun.autodesk.com` resolves. No regional hostname is documented; whether a
  European-hosted site keeps its `shotgrid.autodesk.com` host is unmeasured.
