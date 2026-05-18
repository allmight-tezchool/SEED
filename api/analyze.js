// ============================================
// 競合サイト Google流入数 自動推定 API（AI抽出版）
// ============================================
// Vercel Serverless Function として動作
// POST /api/analyze にURLを送ると、
// AIによるキーワード推定 → 順位確認 → 流入推定 を全部自動でやる
//
// 必要な環境変数:
//   ANTHROPIC_API_KEY ... Claude APIキー（Vercelの環境変数として設定）

import * as cheerio from 'cheerio';

// ============================================
// 設定値
// ============================================

// 使用するClaudeモデル（Haiku 4.5）
const CLAUDE_MODEL = 'claude-haiku-4-5-20251001';

// User-Agentのプール（ブロック回避用にランダムで切り替える）
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
];

// 検索順位ごとのクリック率（Advanced Web Ranking 公開データ参考）
const CTR_BY_POSITION = {
  1: 0.273, 2: 0.155, 3: 0.099, 4: 0.069, 5: 0.051,
  6: 0.038, 7: 0.030, 8: 0.025, 9: 0.020, 10: 0.018,
};
const CTR_OUT_OF_TOP10 = 0.005;

// 1回の調査で確認するキーワードの上限
const MAX_KEYWORDS_TO_CHECK = 10;

// ============================================
// ユーティリティ
// ============================================

function pickUserAgent() {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function randomSleep(min, max) {
  const ms = min + Math.floor(Math.random() * (max - min));
  return sleep(ms);
}

function getDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return null;
  }
}

// ============================================
// ステップ1: サイトの内容を取得（HTMLからAIに渡すテキストを準備）
// ============================================

async function fetchSiteContent(targetUrl) {
  const res = await fetch(targetUrl, {
    headers: {
      'User-Agent': pickUserAgent(),
      'Accept': 'text/html,application/xhtml+xml',
      'Accept-Language': 'ja,en;q=0.9',
    },
  });
  if (!res.ok) {
    throw new Error(`サイト取得失敗: ${res.status}`);
  }
  const html = await res.text();
  const $ = cheerio.load(html);

  // AI入力用にサイトの主要テキストを抽出（HTMLそのままだとトークンを浪費するため）
  const content = {
    url: targetUrl,
    title: $('title').text().trim(),
    metaDescription: $('meta[name="description"]').attr('content') || '',
    metaKeywords: $('meta[name="keywords"]').attr('content') || '',
    ogTitle: $('meta[property="og:title"]').attr('content') || '',
    ogDescription: $('meta[property="og:description"]').attr('content') || '',
    headings: {
      h1: $('h1').map((_, el) => $(el).text().trim()).get().filter(Boolean).slice(0, 5),
      h2: $('h2').map((_, el) => $(el).text().trim()).get().filter(Boolean).slice(0, 15),
      h3: $('h3').map((_, el) => $(el).text().trim()).get().filter(Boolean).slice(0, 15),
    },
    // 本文の冒頭（pタグの内容を結合して2000文字に絞る）
    bodySnippet: $('p').map((_, el) => $(el).text().trim()).get().filter(Boolean).join(' ').slice(0, 2000),
  };

  return content;
}

// ============================================
// ステップ2: Claude Haikuでキーワード抽出
// ============================================

async function extractKeywordsWithAI(siteContent) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error('ANTHROPIC_API_KEYが設定されていません（Vercelの環境変数を確認してください）');
  }

  // AIへの入力プロンプトを構築
  const siteSummary = `
URL: ${siteContent.url}
タイトル: ${siteContent.title}
meta description: ${siteContent.metaDescription}
meta keywords: ${siteContent.metaKeywords}
og:title: ${siteContent.ogTitle}
og:description: ${siteContent.ogDescription}

H1見出し:
${siteContent.headings.h1.map(h => '- ' + h).join('\n')}

H2見出し:
${siteContent.headings.h2.map(h => '- ' + h).join('\n')}

H3見出し:
${siteContent.headings.h3.map(h => '- ' + h).join('\n')}

本文抜粋（冒頭2000文字）:
${siteContent.bodySnippet}
`.trim();

  const prompt = `以下は競合分析対象のウェブサイトの情報です。このサイトが「Google検索で集客するために狙っていそうな日本語キーワード」を推測してください。

【ルール】
- 抽出するキーワード数: ちょうど ${MAX_KEYWORDS_TO_CHECK} 個
- 各キーワードは2〜4語の組み合わせが望ましい（例: "SES 営業 ノウハウ"、"エンジニア 派遣 単価"）
- このサイトのサービス・商品・コンテンツに直結し、かつ検索ボリュームが見込めるキーワードを優先
- ブランド名そのもの（社名等）は除外
- 抽象的すぎる単語（"サービス" "会社" 単体）は避ける
- 出力は必ず以下のJSON形式のみ。前後に文章は付けない

【出力形式】
{
  "keywords": [
    {"keyword": "キーワード1", "intent": "情報収集|比較検討|購入|採用|その他", "estimated_volume": "高|中|低"},
    {"keyword": "キーワード2", "intent": "...", "estimated_volume": "..."}
  ]
}

【estimated_volumeの基準】
- 高: 月間検索数1万回以上（短く一般的）
- 中: 月間検索数1000〜1万回（業界用語、地域+業種など）
- 低: 月間検索数1000回未満（ロングテール、ニッチ用語）

【サイト情報】
${siteSummary}`;

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: CLAUDE_MODEL,
      max_tokens: 1024,
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Claude API エラー (${res.status}): ${errText.slice(0, 200)}`);
  }

  const data = await res.json();
  const text = data.content?.[0]?.text || '';

  // JSON部分だけ抜き出す（前後に文章が混じった場合に備えて）
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error('AI応答からJSONを抽出できませんでした');
  }

  const parsed = JSON.parse(jsonMatch[0]);
  if (!Array.isArray(parsed.keywords)) {
    throw new Error('AI応答の形式が不正です');
  }

  // 入力トークン・出力トークン数の記録（デバッグ用）
  const usage = {
    inputTokens: data.usage?.input_tokens || 0,
    outputTokens: data.usage?.output_tokens || 0,
  };

  return {
    keywords: parsed.keywords.slice(0, MAX_KEYWORDS_TO_CHECK),
    usage,
  };
}

// ============================================
// ステップ2-fallback: AI失敗時の従来方式キーワード抽出
// ============================================

function extractKeywordsFromHTML(siteContent) {
  const phraseScores = new Map();

  function addPhrase(phrase, weight) {
    const cleaned = phrase
      .replace(/\s+/g, ' ')
      .replace(/[【】「」『』\[\]（）()｜|｜\/\\<>"']/g, ' ')
      .trim();
    if (!cleaned || cleaned.length < 3 || cleaned.length > 30) return;
    if (!/[一-龯ぁ-んァ-ヶa-zA-Z]/.test(cleaned)) return;
    phraseScores.set(cleaned, (phraseScores.get(cleaned) || 0) + weight);
  }

  const sources = [
    { text: siteContent.title, weight: 5 },
    { text: siteContent.metaDescription, weight: 4 },
    { text: siteContent.metaKeywords, weight: 5 },
    { text: siteContent.ogTitle, weight: 4 },
    ...siteContent.headings.h1.map(t => ({ text: t, weight: 4 })),
    ...siteContent.headings.h2.map(t => ({ text: t, weight: 3 })),
    ...siteContent.headings.h3.map(t => ({ text: t, weight: 2 })),
  ];

  for (const { text, weight } of sources) {
    if (!text) continue;
    text.split(/[,、，｜|\/／]/).forEach(part => addPhrase(part.trim(), weight));
  }

  const ranked = [...phraseScores.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_KEYWORDS_TO_CHECK);

  return {
    keywords: ranked.map(([phrase]) => ({
      keyword: phrase,
      intent: 'その他',
      estimated_volume: '中',
    })),
    usage: { inputTokens: 0, outputTokens: 0 },
  };
}

// ============================================
// ステップ3: Google検索で順位を確認
// ============================================

async function checkRankOnGoogle(keyword, targetDomain) {
  const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(keyword)}&hl=ja&gl=jp&num=20`;
  await randomSleep(1000, 3000);

  let res;
  try {
    res = await fetch(searchUrl, {
      headers: {
        'User-Agent': pickUserAgent(),
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'ja,en;q=0.9',
      },
    });
  } catch (e) {
    return { rank: null, error: 'fetch-failed' };
  }

  if (res.status === 429 || res.status === 503) {
    return { rank: null, error: 'blocked', status: res.status };
  }
  if (!res.ok) {
    return { rank: null, error: `status-${res.status}` };
  }

  const html = await res.text();
  const $ = cheerio.load(html);

  let rank = null;
  let position = 0;
  const seenDomains = new Set();

  $('a').each((_, el) => {
    if (rank !== null) return;
    let href = $(el).attr('href') || '';
    if (href.startsWith('/url?')) {
      const match = href.match(/[?&]q=([^&]+)/);
      if (match) href = decodeURIComponent(match[1]);
    }
    if (!href.startsWith('http')) return;
    if (href.includes('google.com') || href.includes('googleusercontent.com')) return;
    if (href.includes('youtube.com/results')) return;
    const hasH3 = $(el).find('h3').length > 0;
    if (!hasH3) return;
    const d = getDomain(href);
    if (!d) return;
    if (seenDomains.has(d)) return;
    seenDomains.add(d);
    position++;
    if (d === targetDomain || d.endsWith('.' + targetDomain) || targetDomain.endsWith('.' + d)) {
      rank = position;
    }
  });

  return { rank, totalChecked: position };
}

// ============================================
// ステップ4: 検索ボリュームの数値化
// ============================================
// AIが返す「高/中/低」を実数値に変換

const VOLUME_MAP = {
  '高': 20000,
  '中': 3000,
  '低': 500,
};

function volumeToNumber(label, keyword) {
  if (VOLUME_MAP[label]) return VOLUME_MAP[label];
  // ラベル不明時は文字数から推定
  if (keyword.length <= 6) return 5000;
  if (keyword.length <= 10) return 1500;
  return 400;
}

// ============================================
// ステップ5: 流入推定
// ============================================

function ctrFor(rank) {
  if (rank === null) return 0;
  if (rank <= 10) return CTR_BY_POSITION[rank];
  if (rank <= 20) return CTR_OUT_OF_TOP10;
  return 0;
}

function estimateTraffic(perKeywordResults) {
  let captured = 0;
  const detail = [];
  for (const r of perKeywordResults) {
    const vol = r.estimatedVolume;
    const ctr = ctrFor(r.rank);
    const traffic = Math.round(vol * ctr);
    captured += traffic;
    detail.push({
      keyword: r.keyword,
      intent: r.intent || 'その他',
      volumeLabel: r.volumeLabel || '中',
      rank: r.rank,
      estimatedVolume: vol,
      ctr: (ctr * 100).toFixed(2) + '%',
      estimatedTraffic: traffic,
      error: r.error || null,
    });
  }
  // AI抽出キーワード10個でカバーできるのは全体の40%程度と仮定（AIで精度が上がるため）
  const captureRate = 0.40;
  const estimatedTotal = Math.round(captured / captureRate);
  return { detail, captured, estimatedTotal };
}

// ============================================
// メインハンドラ
// ============================================

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'POSTのみ対応' });
    return;
  }

  try {
    const { url } = req.body || {};
    if (!url) { res.status(400).json({ error: 'urlパラメータが必須です' }); return; }

    const targetDomain = getDomain(url);
    if (!targetDomain) { res.status(400).json({ error: 'URLの形式が不正です' }); return; }

    // ステップ1: サイト取得
    const siteContent = await fetchSiteContent(url);

    // ステップ2: AIでキーワード抽出（失敗時はHTML抽出にフォールバック）
    let keywordsData;
    let extractionMethod = 'ai';
    let aiError = null;
    try {
      keywordsData = await extractKeywordsWithAI(siteContent);
    } catch (e) {
      aiError = e.message;
      console.error('AI抽出失敗、フォールバック:', e.message);
      keywordsData = extractKeywordsFromHTML(siteContent);
      extractionMethod = 'fallback';
    }

    if (keywordsData.keywords.length === 0) {
      res.status(200).json({
        url, title: siteContent.title, keywords: [], result: null,
        warning: 'キーワードを抽出できませんでした。',
      });
      return;
    }

    // ステップ3: 各キーワードの順位確認
    const perKeywordResults = [];
    let blockedCount = 0;
    for (const kw of keywordsData.keywords) {
      const keyword = kw.keyword;
      const volumeLabel = kw.estimated_volume || '中';
      const intent = kw.intent || 'その他';
      const estimatedVolume = volumeToNumber(volumeLabel, keyword);

      const rankInfo = await checkRankOnGoogle(keyword, targetDomain);

      if (rankInfo.error === 'blocked') {
        blockedCount++;
        await sleep(5000);
        const retry = await checkRankOnGoogle(keyword, targetDomain);
        perKeywordResults.push({
          keyword, intent, volumeLabel, estimatedVolume,
          rank: retry.rank, error: retry.error,
        });
      } else {
        perKeywordResults.push({
          keyword, intent, volumeLabel, estimatedVolume,
          rank: rankInfo.rank, error: rankInfo.error,
        });
      }
    }

    // ステップ4: 流入推定
    const trafficResult = estimateTraffic(perKeywordResults);

    res.status(200).json({
      url,
      domain: targetDomain,
      title: siteContent.title,
      keywordsCount: keywordsData.keywords.length,
      extractionMethod,
      aiError,
      aiUsage: keywordsData.usage,
      blocked: blockedCount,
      result: trafficResult,
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message || 'サーバーエラー' });
  }
}
ath.round(captured / captureRate);
  return { detail, captured, estimatedTotal };
}

// ============================================
// メインハンドラ
// ============================================

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.status(200).end(); return; }
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'POSTのみ対応' });
    return;
  }

  try {
    const { url } = req.body || {};
    if (!url) { res.status(400).json({ error: 'urlパラメータが必須です' }); return; }

    const targetDomain = getDomain(url);
    if (!targetDomain) { res.status(400).json({ error: 'URLの形式が不正です' }); return; }

    // ステップ1: サイト取得
    const siteContent = await fetchSiteContent(url);

    // ステップ2: AIでキーワード抽出（失敗時はHTML抽出にフォールバック）
    let keywordsData;
    let extractionMethod = 'ai';
    let aiError = null;
    try {
      keywordsData = await extractKeywordsWithAI(siteContent);
    } catch (e) {
      aiError = e.message;
      console.error('AI抽出失敗、フォールバック:', e.message);
      keywordsData = extractKeywordsFromHTML(siteContent);
      extractionMethod = 'fallback';
    }

    if (keywordsData.keywords.length === 0) {
      res.status(200).json({
        url, title: siteContent.title, keywords: [], result: null,
        warning: 'キーワードを抽出できませんでした。',
      });
      return;
    }

    // ステップ3: 各キーワードの順位確認
    const perKeywordResults = [];
    let blockedCount = 0;
    for (const kw of keywordsData.keywords) {
      const keyword = kw.keyword;
      const volumeLabel = kw.estimated_volume || '中';
      const intent = kw.intent || 'その他';
      const estimatedVolume = volumeToNumber(volumeLabel, keyword);

      const rankInfo = await checkRankOnGoogle(keyword, targetDomain);

      if (rankInfo.error === 'blocked') {
        blockedCount++;
        await sleep(5000);
        const retry = await checkRankOnGoogle(keyword, targetDomain);
        perKeywordResults.push({
          keyword, intent, volumeLabel, estimatedVolume,
          rank: retry.rank, error: retry.error,
        });
      } else {
        perKeywordResults.push({
          keyword, intent, volumeLabel, estimatedVolume,
          rank: rankInfo.rank, error: rankInfo.error,
        });
      }
    }

    // ステップ4: 流入推定
    const trafficResult = estimateTraffic(perKeywordResults);

    res.status(200).json({
      url,
      domain: targetDomain,
      title: siteContent.title,
      keywordsCount: keywordsData.keywords.length,
      extractionMethod,
      aiError,
      aiUsage: keywordsData.usage,
      blocked: blockedCount,
      result: trafficResult,
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message || 'サーバーエラー' });
  }
}
