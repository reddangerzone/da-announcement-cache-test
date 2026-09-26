const SWITCH_AT = Date.parse("2026-09-26T19:00:00Z");

function image(version) {
  const after = version === "after";
  const background = after ? "#087f84" : "#6b315f";
  const accent = after ? "#ffd83d" : "#62e6d5";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675">
    <defs>
      <radialGradient id="glow" cx="50%" cy="40%" r="70%"><stop offset="0" stop-color="__ACCENT__" stop-opacity=".32"/><stop offset="1" stop-color="#11151d" stop-opacity="0"/></radialGradient>
      <filter id="shadow"><feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#000" flood-opacity=".35"/></filter>
    </defs>
    <rect width="1200" height="675" rx="36" fill="__BACKGROUND__"/>
    <rect width="1200" height="675" rx="36" fill="url(#glow)"/>
    <g transform="translate(165 337)" filter="url(#shadow)">
      <path d="M0 115 C-105 45 -135 -35 -75 -80 C-30 -112 5 -82 20 -48 C38 -83 73 -112 116 -80 C178 -34 145 47 40 115 L20 129Z" fill="#f58b9e" stroke="#fff3e7" stroke-width="10"/>
      <g transform="translate(-2 -15)">
        <ellipse cx="22" cy="0" rx="80" ry="68" fill="#8f6049" stroke="#fff3e7" stroke-width="8"/>
        <path d="M-54 -25l-52 -28 22 55-42 18 66 9M98 -25l52 -28-22 55 42 18-66 9" fill="#d99d80" stroke="#fff3e7" stroke-width="7" stroke-linejoin="round"/>
        <circle cx="-8" cy="-9" r="9" fill="#171920"/><circle cx="52" cy="-9" r="9" fill="#171920"/>
        <path d="M3 20 Q22 37 42 20" fill="none" stroke="#171920" stroke-width="7" stroke-linecap="round"/>
        <circle cx="-29" cy="19" r="10" fill="#f3a0a7" opacity=".8"/><circle cx="73" cy="19" r="10" fill="#f3a0a7" opacity=".8"/>
      </g>
    </g>
    <text x="675" y="295" text-anchor="middle" fill="#f7f3e8" font-family="Arial,sans-serif" font-size="72" font-weight="800">Red is Testing</text>
    <text x="675" y="385" text-anchor="middle" fill="__ACCENT__" font-family="Arial,sans-serif" font-size="92" font-weight="900">Something</text>
    <text x="675" y="445" text-anchor="middle" fill="#f7f3e8" font-family="Arial,sans-serif" font-size="25" opacity=".82">If this color changes, Torn refreshed the image ✨</text>
  </svg>`;
  return svg.replaceAll("__ACCENT__", accent).replaceAll("__BACKGROUND__", background);
}

export default async () => {
  const version = Date.now() >= SWITCH_AT ? "after" : "before";
  return new Response(image(version), {
    status: 200,
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
      "CDN-Cache-Control": "no-store",
      "Netlify-CDN-Cache-Control": "no-store",
      "Pragma": "no-cache",
      "Expires": "0",
      "X-Announcement-Version": version,
      "X-Switch-At": "2026-09-26T19:00:00Z"
    }
  });
};

export const config = { path: "/announcement-test.svg" };
