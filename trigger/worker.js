export default {
  async scheduled(controller, env, ctx) {
    if (!env.GITHUB_TOKEN) throw new Error('Missing dispatch credential');
    const response = await fetch('https://api.github.com/repos/ins-labs/ins-clock/actions/workflows/clock.yml/dispatches', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.GITHUB_TOKEN}`,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2026-03-10',
        'User-Agent': 'ins-clock-cloudflare-trigger',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ref: 'main' })
    });
    console.log(JSON.stringify({source:'cloudflare-cron', scheduledTime:controller.scheduledTime, status:response.status}));
    if (![200, 204].includes(response.status)) throw new Error(`Dispatch failed: HTTP ${response.status}`);
  },
  async fetch() {
    return new Response('ins-clock trigger: cron only\n', {headers:{'Content-Type':'text/plain'}});
  }
};
