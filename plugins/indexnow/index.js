// IndexNow, after the deploy is live (Program 8, Sprint 8.2, item 5). The build wrote the changed
// URLs to out/indexnow-changed.json; this sends them. It logs the response and never fails a deploy.
const { execFileSync } = require('child_process');

module.exports = {
  onSuccess() {
    try {
      const out = execFileSync('python3', ['indexnow.py', '--send'], { encoding: 'utf8', timeout: 60000 });
      console.log(out.trim());
    } catch (e) {
      console.log('indexnow: send step did not run (' + String(e.message).split('\n')[0] + '); the next build sends again');
    }
  },
};
