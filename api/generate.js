// api/generate.js — Vercel Serverless Function

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { prompt, max_tokens } = req.body;
  if (!prompt) return res.status(400).json({ error: 'No prompt provided' });

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'ANTHROPIC_API_KEY not set in Vercel environment variables.' });

  // Try models in order — fallback if one fails
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
          break; // try next model
        }

        if (response.status === 404 || response.status === 400) {
          lastError = `Model ${model} not available: ` + (data?.error?.message || '');
          break; // try next model immediately
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
