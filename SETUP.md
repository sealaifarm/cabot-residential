# Setting up the Cabot Residential admin panel

This is a one-time setup, done by whoever manages the website (not the
day-to-day admin user). Once it's done, the person using the admin panel
will only ever see a password screen and a clean interface for managing
developments — no technical details.

There are two pieces:

1. **`worker.js`** — a small backend that holds all the secret keys and
   talks to GitHub and Cloudflare on the admin panel's behalf.
2. **`admin.html`** — the admin panel itself, a single page you host
   anywhere (it can even sit right next to `index.html` on the same site,
   e.g. as `/admin.html`).

---

## 1. Deploy the backend (Cloudflare Worker)

You'll need a free Cloudflare account and `wrangler`, Cloudflare's
command-line tool.

```bash
npm install -g wrangler
wrangler login
cd admin
wrangler deploy
```

This publishes the worker and gives you a URL like:

```
https://cabot-admin.your-subdomain.workers.dev
```

Keep that URL — you'll need it in step 3.

### Set the secrets

These are never stored in any file — they live only inside Cloudflare.

```bash
wrangler secret put ADMIN_PASSWORD
wrangler secret put GITHUB_TOKEN
wrangler secret put GITHUB_OWNER
wrangler secret put GITHUB_REPO
wrangler secret put GITHUB_BRANCH
wrangler secret put GITHUB_FILE_PATH
wrangler secret put CF_ACCOUNT_ID
wrangler secret put CF_IMAGES_TOKEN
```

You'll be prompted to paste each value. Here's what each one is:

| Secret | What to enter |
|---|---|
| `ADMIN_PASSWORD` | Whatever password you want the admin panel to use. |
| `GITHUB_TOKEN` | A GitHub personal access token (fine-grained, scoped to just this one repo) with read/write access to contents. Create one at github.com → Settings → Developer settings → Personal access tokens. |
| `GITHUB_OWNER` | The GitHub username or organization that owns the website repo. |
| `GITHUB_REPO` | The name of the repo, e.g. `cabot-website`. |
| `GITHUB_BRANCH` | The branch the live site deploys from, usually `main`. |
| `GITHUB_FILE_PATH` | The path to the JSON file in that repo, e.g. `projects.json`. |
| `CF_ACCOUNT_ID` | Found in the Cloudflare dashboard sidebar (any page, bottom right). |
| `CF_IMAGES_TOKEN` | An API token with "Cloudflare Images: Edit" permission. Create at Cloudflare dashboard → My Profile → API Tokens. Requires the Cloudflare Images add-on to be enabled on the account. |

That's it for the backend — it will now quietly hold all of this and
never expose it anywhere.

---

## 2. Point the admin panel at your worker

Open `admin.html` and find this line near the top of the `<script>` block:

```js
const WORKER_URL = "https://cabot-admin.YOUR-SUBDOMAIN.workers.dev";
```

Replace it with the actual URL from step 1. This is the only edit needed.

---

## 3. Host the admin panel

Upload `admin.html` alongside the existing site files (same place as
`index.html`, `project.html`, etc.) — for example as `/admin.html`. It
doesn't need to be linked from the public site; just share the URL with
whoever will use it.

---

## Day-to-day use

From here on, using the admin panel is just:

1. Go to `yoursite.com/admin.html`
2. Enter the password
3. Click a development to edit it, or "Add a development" to create one
4. Change info, drag photos to reorder, add/remove/replace photos
5. Click **Publish changes** when ready — this updates the live website

Nothing about GitHub, repos, branches, file paths, or Cloudflare ever
appears in the admin panel itself. All of that setup happens once, here,
and stays behind the scenes after that.
