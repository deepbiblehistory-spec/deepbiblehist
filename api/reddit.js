// api/reddit.js — Server-side Reddit proxy for DBH Intelligence Tool
// Vercel serverless can reach Reddit; browsers cannot (CORS blocked)

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();

  const { subreddit, sort, time, limit } = req.method === 'POST'
    ? req.body
    : req.query;

  if (!subreddit) return res.status(400).json({ error: 'subreddit required' });

  const sortPath = sort || 'hot';
  const timeParam = time ? `&t=${time}` : '';
  const limitParam = limit || 50;

  const url = `https://www.reddit.com/r/${subreddit}/${sortPath}.json?limit=${limitParam}${timeParam}&raw_json=1`;

  try {
    const response = await fetch(url, {
      headers: {
        'User-Agent': 'DBH-Intelligence/1.0 (biblical history research tool)',
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      return res.status(response.status).json({
        error: `Reddit returned ${response.status}`,
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
        url:          p.url,
        flair:        p.link_flair_text || '',
        created_utc:  p.created_utc,
        selftext:     (p.selftext || '').slice(0, 300),
        is_self:      p.is_self,
      }));

    return res.status(200).json({ success: true, posts, subreddit, count: posts.length });

  } catch (err) {
    return res.status(500).json({ error: err.message || 'Fetch failed' });
  }
}
