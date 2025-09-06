import fs from "node:fs";
const limitKB = 200;
const stats = JSON.parse(fs.readFileSync(".next/analyze/client-stats.json","utf8"));
const total = Math.round(stats.totalGzipSize/1024);
if (total > limitKB) { console.error(`Initial JS ${total}KB > ${limitKB}KB`); process.exit(1); }
console.log(`Initial JS OK: ${total}KB`);
