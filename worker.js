/**
 * Cabot Residential — Admin backend
 * ----------------------------------
 * This is a small Cloudflare Worker that sits between the admin panel
 * (admin.html) and two outside services: GitHub (where projects.json
 * lives) and an R2 bucket (where uploaded photos are stored).
 *
 * It exists so that no API keys, tokens, repo names, or file paths are
 * ever visible to the person using the admin panel — everything
 * sensitive lives here, as Worker secrets, configured once.
 *
 * Endpoints:
 *   POST /api/login      { password }              -> 200 / 401
 *   GET  /api/projects                              -> { projects, sha }
 *   PUT  /api/projects   { projects, sha, message }  -> { sha }
 *   POST /api/upload     multipart file              -> { url }
 *   GET  /images/<key>   public, no auth             -> the stored photo
 *
 * Every request under /api (except /api/login) must include header:
 *   X-Admin-Key: <the admin password>
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    try {
      if (url.pathname === '/api/login' && request.method === 'POST') {
        return await handleLogin(request, env);
      }

      // public route — serves uploaded photos from R2, no admin key needed
      if (url.pathname.startsWith('/images/') && request.method === 'GET') {
        return await getImage(url, env);
      }

      // everything below requires a valid admin key
      const key = request.headers.get('X-Admin-Key') || '';
      if (!timingSafeEqual(key, env.ADMIN_PASSWORD)) {
        return json({ error: 'Unauthorized' }, 401);
      }

      if (url.pathname === '/api/projects' && request.method === 'GET') {
        return await getProjects(env);
      }
      if (url.pathname === '/api/projects' && request.method === 'PUT') {
        return await putProjects(request, env);
      }
      if (url.pathname === '/api/upload' && request.method === 'POST') {
        return await uploadImage(request, env);
      }

      return json({ error: 'Not found' }, 404);
    } catch (err) {
      return json({ error: err.message || 'Server error' }, 500);
    }
  }
};

/* ---------------------------------------------------------- */

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Key'
  };
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() }
  });
}
function timingSafeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

async function handleLogin(request, env) {
  const body = await request.json().catch(() => ({}));
  if (timingSafeEqual(body.password || '', env.ADMIN_PASSWORD)) {
    return json({ ok: true });
  }
  return json({ error: 'Incorrect password' }, 401);
}

/* ---------------------------------------------------------- */
/* GitHub — projects.json lives in a repo, edited via the
   Contents API using a Personal Access Token stored as a secret. */

function githubApiUrl(env) {
  return `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/contents/${env.GITHUB_FILE_PATH}`;
}
function githubHeaders(env) {
  return {
    'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
    'User-Agent': 'cabot-admin-worker',
    'Accept': 'application/vnd.github+json'
  };
}

async function getProjects(env) {
  const res = await fetch(`${githubApiUrl(env)}?ref=${env.GITHUB_BRANCH || 'main'}`, {
    headers: githubHeaders(env)
  });
  if (!res.ok) throw new Error('Could not load developments from GitHub');
  const data = await res.json();
  const content = decodeBase64Utf8(data.content);
  return json({ projects: JSON.parse(content), sha: data.sha });
}

async function putProjects(request, env) {
  const body = await request.json();
  const { projects, sha, message } = body;
  if (!Array.isArray(projects)) throw new Error('Invalid data — expected a list of developments');

  const content = encodeBase64Utf8(JSON.stringify(projects, null, 2) + '\n');

  const res = await fetch(githubApiUrl(env), {
    method: 'PUT',
    headers: { ...githubHeaders(env), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message || 'Update developments via admin panel',
      content,
      sha: sha || undefined,
      branch: env.GITHUB_BRANCH || 'main'
    })
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    if (res.status === 409 || /does not match|sha/i.test(errBody)) {
      throw new Error('Someone else published changes just now — please reload and try again.');
    }
    throw new Error('Could not publish to GitHub');
  }
  const data = await res.json();
  return json({ sha: data.content?.sha });
}

function decodeBase64Utf8(b64) {
  const cleaned = b64.replace(/\n/g, '');
  const bytes = Uint8Array.from(atob(cleaned), c => c.charCodeAt(0));
  return new TextDecoder('utf-8').decode(bytes);
}
function encodeBase64Utf8(str) {
  const bytes = new TextEncoder().encode(str);
  let binary = '';
  bytes.forEach(b => binary += String.fromCharCode(b));
  return btoa(binary);
}

/* ---------------------------------------------------------- */
/* R2 — photo uploads land in the IMAGES bucket. Since R2 Public
   Access is disabled, this same Worker serves them back out at
   GET /images/<key> so the public Netlify site can load them. */

async function uploadImage(request, env) {
  const incoming = await request.formData();
  const file = incoming.get('file');
  if (!file) throw new Error('No file received');

  const key = makeImageKey(file.name || 'photo.jpg');

  await env.IMAGES.put(key, file.stream(), {
    httpMetadata: {
      contentType: file.type || 'application/octet-stream'
    }
  });

  const url = new URL(request.url);
  const publicUrl = `${url.origin}/images/${key}`;
  return json({ url: publicUrl });
}

function makeImageKey(originalName) {
  const dot = originalName.lastIndexOf('.');
  const ext = dot !== -1 ? originalName.slice(dot + 1).toLowerCase().replace(/[^a-z0-9]/g, '') : '';
  const id = crypto.randomUUID();
  return ext ? `${id}.${ext}` : id;
}

async function getImage(url, env) {
  const key = decodeURIComponent(url.pathname.replace(/^\/images\//, ''));
  if (!key) return json({ error: 'Not found' }, 404);

  const object = await env.IMAGES.get(key);
  if (!object) return json({ error: 'Not found' }, 404);

  const headers = new Headers();
  object.writeHttpMetadata(headers);
  headers.set('Cache-Control', 'public, max-age=31536000, immutable');
  headers.set('ETag', object.httpEtag);
  headers.set('Access-Control-Allow-Origin', '*');

  return new Response(object.body, { headers });
}
