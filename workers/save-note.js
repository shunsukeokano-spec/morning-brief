/**
 * Cloudflare Worker: save Shun's daily note to daily_note.md via GitHub API.
 *
 * Required environment variable (set as Worker Secret):
 *   GITHUB_TOKEN — fine-grained PAT with Contents:read+write on morning-brief repo
 *
 * Deploy:
 *   1. Create Worker at dash.cloudflare.com → Workers & Pages → Create
 *   2. Paste this file
 *   3. Settings → Variables → Add secret: GITHUB_TOKEN
 *   4. Copy the Worker URL and add it as GitHub Secret NOTE_WORKER_URL
 */

const REPO = 'shunsukeokano-spec/morning-brief';
const FILE = 'daily_note.md';
const ALLOWED_ORIGIN = 'https://shunsukeokano-spec.github.io';

const CORS = {
  'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: CORS });
    }

    let note;
    try {
      ({ note } = await request.json());
    } catch {
      return new Response('Invalid JSON', { status: 400, headers: CORS });
    }

    if (!note || !note.trim()) {
      return new Response('Empty note', { status: 400, headers: CORS });
    }

    const apiBase = `https://api.github.com/repos/${REPO}/contents/${FILE}`;
    const headers = {
      'Authorization': `token ${env.GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'morning-brief-worker',
    };

    // Get current SHA
    const getRes = await fetch(apiBase, { headers });
    if (!getRes.ok) {
      return new Response('Failed to read file', { status: 502, headers: CORS });
    }
    const { sha } = await getRes.json();

    // Write updated content
    const content = [
      '<!-- 今日のブリーフを読んで気になったこと・質問を1行ここに書く。翌朝のブリーフに反映される。 -->',
      '',
      note.trim(),
      '',
    ].join('\n');

    const date = new Date().toISOString().split('T')[0];
    const putRes = await fetch(apiBase, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        message: `Daily note ${date}`,
        content: btoa(unescape(encodeURIComponent(content))),
        sha,
      }),
    });

    if (putRes.ok) {
      return new Response(JSON.stringify({ ok: true }), {
        headers: { ...CORS, 'Content-Type': 'application/json' },
      });
    }

    const err = await putRes.text();
    return new Response(JSON.stringify({ ok: false, error: err }), {
      status: 502,
      headers: { ...CORS, 'Content-Type': 'application/json' },
    });
  },
};
