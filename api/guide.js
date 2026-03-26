// api/guide.js — Bible Study Guide PDF Generator

import { exec } from 'child_process';
import { writeFileSync, readFileSync, unlinkSync } from 'fs';
import { promisify } from 'util';
import path from 'path';
import os from 'os';

const execAsync = promisify(exec);

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { text, topic, guide_type } = req.body;
  if (!text || !topic) return res.status(400).json({ error: 'Missing text or topic' });

  const tmpDir    = os.tmpdir();
  const inputFile = path.join(tmpDir, `guide_input_${Date.now()}.json`);
  const outputFile = path.join(tmpDir, `guide_output_${Date.now()}.pdf`);

  try {
    // Write input JSON
    writeFileSync(inputFile, JSON.stringify({ text, topic, guide_type: guide_type || 'Study Guide', output: outputFile }));

    // Run Python PDF builder
    const script = path.join(process.cwd(), 'api', 'build_guide_pdf.py');
    await execAsync(`python3 ${script} < ${inputFile}`, { timeout: 60000 });

    // Read PDF and return as base64
    const pdfBuffer = readFileSync(outputFile);
    const pdfBase64 = pdfBuffer.toString('base64');

    // Cleanup
    try { unlinkSync(inputFile); unlinkSync(outputFile); } catch(e) {}

    res.setHeader('Content-Type', 'application/json');
    return res.status(200).json({ success: true, pdf: pdfBase64, filename: `DBH-Study-Guide-${topic.slice(0,40).replace(/[^a-zA-Z0-9]/g,'-')}.pdf` });

  } catch (err) {
    try { unlinkSync(inputFile); } catch(e) {}
    try { unlinkSync(outputFile); } catch(e) {}
    return res.status(500).json({ error: err.message || 'PDF generation failed' });
  }
}
