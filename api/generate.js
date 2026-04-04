// api/generate.js — Vercel Serverless Function
// Handles: AI generation (text + image) + Reddit Intelligence

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body;
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'ANTHROPIC_API_KEY not set' });

  const MODELS = [
    'claude-haiku-4-5-20251001',
    'claude-haiku-3-5-20241022',
  ];

  // ── REDDIT INTELLIGENCE via Claude Web Search ─────────────────────────
  if (body.action === 'reddit') {
    const { subreddit, sort, time, limit } = body;
    if (!subreddit) return res.status(400).json({ error: 'subreddit required' });

    const timeLabel = { month:'this month', week:'this week', year:'this year', all:'all time' }[time] || 'recently';
    const sortLabel = sort === 'top' ? `top posts ${timeLabel}` : sort === 'hot' ? 'hot posts right now' : sort === 'new' ? 'newest posts' : 'trending posts';
    const count = parseInt(limit) || 25;

    const searchPrompt = `Search Reddit r/${subreddit} and find the ${sortLabel}. Return the ${count} most engaging posts.

For each post use EXACTLY this format:
---POST---
TITLE: [exact post title]
SCORE: [upvote number]
COMMENTS: [comment count]
FLAIR: [flair if any]
---END---

Find real posts from r/${subreddit}. Focus on biblical history, archaeology, theology, scripture topics. Return up to ${count} posts.`;

    let lastErr = '';
    for (const model of MODELS) {
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
            max_tokens: 4000,
            tools: [{ type: 'web_search_20250305', name: 'web_search' }],
            messages: [{ role: 'user', content: searchPrompt }]
          })
        });

        const data = await response.json().catch(() => ({}));

        if (response.status === 404 || response.status === 400) {
          lastErr = `${model} not available: ` + (data?.error?.message || '');
          continue;
        }
        if (!response.ok) {
          lastErr = `${model} error ${response.status}`;
          continue;
        }

        const fullText = (data.content || []).map(b => b.type === 'text' ? b.text : '').join('\n');

        const posts = [];
        const blocks = fullText.split('---POST---').slice(1);
        for (const block of blocks) {
          const end = block.indexOf('---END---');
          const chunk = end > -1 ? block.slice(0, end) : block;
          const get = (field) => {
            const m = chunk.match(new RegExp(field + ':\\s*(.+?)(?=\\n[A-Z]+:|$)', 's'));
            return m ? m[1].trim() : '';
          };
          const parseNum = (s) => {
            if (!s) return 0;
            s = s.replace(/[^0-9.KkMm]/g, '');
            if (/k$/i.test(s)) return Math.round(parseFloat(s) * 1000);
            if (/m$/i.test(s)) return Math.round(parseFloat(s) * 1000000);
            return parseInt(s) || 0;
          };
          const title = get('TITLE');
          if (title && title.length > 3) {
            posts.push({
              title,
              score: parseNum(get('SCORE')),
              num_comments: parseNum(get('COMMENTS')),
              permalink: `/r/${subreddit}/`,
              flair: get('FLAIR'),
              created_utc: Date.now() / 1000,
            });
          }
        }

        if (posts.length > 0) {
          return res.status(200).json({ success: true, posts, subreddit, count: posts.length });
        }
        if (fullText.length > 50) {
          return res.status(200).json({ success: true, posts: [], rawText: fullText, subreddit, count: 0 });
        }

      } catch (err) {
        lastErr = `${model} exception: ` + err.message;
      }
    }
    return res.status(500).json({ error: 'Reddit search failed: ' + lastErr });
  }

  // ── AI GENERATION (text + optional image) ─────────────────────────────
  const { prompt, max_tokens, image_base64, image_mime } = body;
  if (!prompt) return res.status(400).json({ error: 'No prompt provided' });

  // Build message content — image+text or text only
  const msgContent = image_base64
    ? [
        {
          type: 'image',
          source: {
            type: 'base64',
            media_type: image_mime || 'image/jpeg',
            data: image_base64
          }
        },
        { type: 'text', text: prompt }
      ]
    : prompt;

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
            messages: [{ role: 'user', content: msgContent }]
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
