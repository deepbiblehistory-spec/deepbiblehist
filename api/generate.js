// api/generate.js — Vercel Serverless Function
// Handles: AI generation (action: 'generate') + Reddit proxy (action: 'reddit')

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body;

  // ── REDDIT PROXY ──────────────────────────────────────────────────────
  if (body.action === 'reddit') {
    const { subreddit, sort, time, limit } = body;
    if (!subreddit) return res.status(400).json({ error: 'subreddit required' });

    const sortPath = sort || 'hot';
    const timeParam = time ? `&t=${time}` : '';
    const limitParam = parseInt(limit) || 50;
    const url = `https://www.reddit.com/r/${subreddit}/${sortPath}.json?limit=${limitParam}${timeParam}&raw_json=1`;

    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': 'DBH-Intelligence/1.0 (biblical history research)',
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        return res.status(response.status).json({
          error: `Reddit returned ${response.status} — subreddit may be private or restricted`,
          detail: text.slice(0, 200)
        });
      }

      const data = await response.json();
      const posts = (data?.data?.children || [])
        .map(c => c.data)
        .filter(p => !p.stickied)
        .map(p => ({
          id:           p.id,
          title:        p.title,
          score:        p.score,
          num_comments: p.num_comments,
          permalink:    p.permalink,
          flair:        p.link_flair_text || '',
          created_utc:  p.created_utc,
          selftext:     (p.selftext || '').slice(0, 300),
        }));

      return res.status(200).json({ success: true, posts, subreddit, count: posts.length });

    } catch (err) {
      return res.status(500).json({ error: 'Reddit fetch failed: ' + err.message });
    }
  }

  // ── AI GENERATION ─────────────────────────────────────────────────────
  const { prompt, max_tokens } = body;
  if (!prompt) return res.status(400).json({ error: 'No prompt provided' });

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'ANTHROPIC_API_KEY not set in Vercel environment variables.' });

  const MODELS = [
    'claude-sonnet-4-5-20251022',
    'claude-haiku-4-5-20251001',
    'claude-3-5-sonnet-20241022',
    'claude-3-5-haiku-20241022',
  ];

  let lastError = '';

  for (const model of MODELS) {
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const response = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
          },
          body: JSON.stringify({
            model,
            max_tokens: max_tokens || 8000,
            messages: [{ role: 'user', content: prompt }]
          })
        });

        const data = await response.json().catch(() => ({}));

        if (response.status === 529 || response.status === 503 || response.status === 429) {
          lastError = `Rate limited on ${model}: ` + (data?.error?.message || '');
          if (attempt < 3) {
            await new Promise(r => setTimeout(r, attempt * 15000));
            continue;
          }
          break;
        }

        if (response.status === 404 || response.status === 400) {
          lastError = `Model ${model} not available: ` + (data?.error?.message || '');
          break;
        }

        if (!response.ok) {
          lastError = `${model} error ${response.status}: ` + (data?.error?.message || '');
          break;
        }

        const text = data.content?.map(b => b.text || '').join('') || '';
        return res.status(200).json({ success: true, text, model });

      } catch (err) {
        lastError = `${model} exception: ` + err.message;
        if (attempt < 3) await new Promise(r => setTimeout(r, attempt * 5000));
      }
    }
  }

  return res.status(500).json({ error: 'All models failed. Last error: ' + lastError });
}
