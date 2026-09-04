import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './sources.js';

// The MCP tool list, read from the server that serves them. The page said four
// tools for as long as there were five: a number written into prose is a number
// that drifts, so this one is measured from `TOOLS` and cannot be edited into
// agreement with a stale claim.
export function mcpToolNames() {
	const src = fs.readFileSync(path.join(REPO_ROOT, 'src', 'sg_groundtruth', 'mcp.py'), 'utf8');
	const block = src.match(/^TOOLS = \[[\s\S]*?^\]/m);
	if (!block) throw new Error('[mcp] no TOOLS list in src/sg_groundtruth/mcp.py');
	const names = [...block[0].matchAll(/^\s+"name": "([a-z_]+)"/gm)].map((m) => m[1]);
	if (!names.length) throw new Error('[mcp] TOOLS list is empty');
	return names;
}
