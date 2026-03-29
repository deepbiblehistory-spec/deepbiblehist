// api/generate.js — Vercel Serverless Function
// Handles: AI generation + Reddit Intelligence (via Claude web search)

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body;
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'ANTHROPIC_API_KEY not set' });

  // ── REDDIT INTELLIGENCE via Claude Web Search ─────────────────────────
  if (body.action === 'reddit') {
    const { subreddit, sort, time, limit } = body;
    if (!subreddit) return res.status(400).json({ error: 'subreddit required' });

    const timeLabel = { month:'this month', week:'this week', year:'this year', all:'all time' }[time] || 'recently';
    const sortLabel = sort === 'top' ? `top posts ${timeLabel}` : sort === 'hot' ? 'hot posts right now' : sort === 'new' ? 'newest posts' : 'trending posts';
    const count = parseInt(limit) || 25;

    const searchPrompt = `Search Reddit r/${subreddit} and find the ${sortLabel}. I need the ${count} most engaging posts.

For each post return EXACTLY this format (one post per block):
---POST---
TITLE: [exact post title]
SCORE: [upvote number]
COMMENTS: [comment count]
URL: https://reddit.com/r/${subreddit}/
FLAIR: [flair tag if any, or blank]
---END---

Find real, actual posts from r/${subreddit}. Focus on posts about biblical history, archaeology, theology, scripture, or related topics. Return as many as you can find up to ${count}.`;

    try {
      // Try models in order — same fallback chain as AI generation
      const REDDIT_MODELS = [
        'claude-haiku-4-5-20251001',
        'claude-sonnet-4-5-20251022',
        'claude-3-5-haiku-20241022',
        'claude-3-5-sonnet-20241022',
      ];

      let response, data;
      let searchError = '';

      for (const rModel of REDDIT_MODELS) {
        response = await fetch('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
          },
          body: JSON.stringify({
            model: rModel,
            max_tokens: 4000,
            tools: [{ type: 'web_search_20250305', name: 'web_search' }],
            messages: [{ role: 'user', content: searchPrompt }]
          })
        });
        data = await response.json().catch(() => ({}));
        if (response.ok) break;
        searchError = `${rModel}: ` + (data?.error?.message || response.status);
      }

      if (!response.ok) {
        return res.status(500).json({ error: 'Claude search failed: ' + searchError });
      }

      // Extract text from all content blocks
      const fullText = (data.content || [])
        .map(b => b.type === 'text' ? b.text : '')
        .join('\n');

      // Parse posts from structured format
      const posts = [];
      const blocks = fullText.split('---POST---').slice(1);
      
      for (const block of blocks) {
        const endIdx = block.indexOf('---END---');
        const content = endIdx > -1 ? block.slice(0, endIdx) : block;
        
        const getField = (field) => {
          const m = content.match(new RegExp(field + ':\\s*(.+?)(?=\\n[A-Z]+:|$)', 's'));
          return m ? m[1].trim() : '';
        };

        const title = getField('TITLE');
        const scoreStr = getField('SCORE').replace(/[^0-9.KkMm]/g, '');
        const commentsStr = getField('COMMENTS').replace(/[^0-9.KkMm]/g, '');
        
        const parseNum = (s) => {
          if (!s) return 0;
          if (s.toLowerCase().endsWith('k')) return Math.round(parseFloat(s) * 1000);
          if (s.toLowerCase().endsWith('m')) return Math.round(parseFloat(s) * 1000000);
          return parseInt(s) || 0;
        };

        if (title && title.length > 3) {
          posts.push({
            title,
            score: parseNum(scoreStr),
            num_comments: parseNum(commentsStr),
            permalink: `/r/${subreddit}/`,
            flair: getField('FLAIR'),
            created_utc: Date.now() / 1000,
          });
        }
      }

      // If structured parsing failed, try to extract from freeform text
      if (posts.length === 0 && fullText.length > 100) {
        // Fallback: send raw text back for client to display
        return res.status(200).json({
          success: true,
          posts: [],
          rawText: fullText,
          subreddit,
          count: 0,
          message: 'Parsed as freeform — see rawText'
        });
      }

      return res.status(200).json({
        success: true,
        posts,
        subreddit,
        count: posts.length,
        source: 'claude-web-search'
      });

    } catch (err) {
      return res.status(500).json({ error: 'Reddit search failed: ' + err.message });
    }
  }

  // ── AI GENERATION ─────────────────────────────────────────────────────
  const { prompt, max_tokens } = body;
  if (!prompt) return res.status(400).json({ error: 'No prompt provided' });

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
