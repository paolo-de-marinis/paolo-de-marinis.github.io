<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9"
  xmlns:xhtml="http://www.w3.org/1999/xhtml"
  exclude-result-prefixes="sm xhtml">
  <xsl:output method="html" encoding="UTF-8" doctype-system="about:legacy-compat" />

  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>XML Sitemap | Paolo De Marinis</title>
        <style>
          :root{color-scheme:light;--ink:#0b1928;--paper:#f4f1e9;--surface:#fffdf8;--muted:#56616b;--line:#0b192833;--accent:#b94722;--mint:#b9ded9}
          *{box-sizing:border-box}html{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55}body{background:var(--paper);color:var(--ink);margin:0}a{color:inherit}.skip{background:var(--ink);color:var(--surface);left:12px;padding:10px 14px;position:fixed;top:12px;transform:translateY(-180%);z-index:2}.skip:focus{transform:none}.site-header{align-items:center;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;margin:auto;min-height:66px;width:min(calc(100% - 48px),1280px)}.wordmark{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-weight:820;letter-spacing:-.05em;text-decoration:none}.wordmark span,.eyebrow{color:var(--accent)}.xml-label{color:var(--muted);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.7rem;font-weight:760;letter-spacing:.09em;text-transform:uppercase}main{margin:auto;padding:clamp(64px,9vw,112px) 0;width:min(calc(100% - 48px),1280px)}.eyebrow{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.7rem;font-weight:760;letter-spacing:.09em;margin:0;text-transform:uppercase}h1{font-size:clamp(3rem,7vw,6.4rem);font-weight:650;letter-spacing:-.07em;line-height:.95;margin:18px 0 24px}.intro{color:var(--muted);font-size:clamp(1.05rem,2vw,1.35rem);max-width:760px}.stats{display:grid;gap:1px;grid-template-columns:repeat(3,1fr);margin:48px 0 30px;background:var(--line);border:1px solid var(--line)}.stat{background:var(--surface);padding:22px 24px}.stat strong{display:block;font-size:1.35rem}.stat span{color:var(--muted);font-size:.78rem}.table-wrap{border:1px solid var(--line);overflow-x:auto;background:var(--surface)}table{border-collapse:collapse;min-width:780px;width:100%}th,td{border-bottom:1px solid var(--line);padding:20px 22px;text-align:left;vertical-align:top}th{background:var(--ink);color:var(--surface);font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase}tr:last-child td{border-bottom:0}.url{font-weight:720;text-decoration-thickness:1px;text-underline-offset:4px}.date{color:var(--muted);white-space:nowrap}.alternates{display:flex;flex-wrap:wrap;gap:8px}.alternate{background:var(--mint);border:1px solid var(--line);border-radius:999px;font-size:.72rem;font-weight:720;padding:6px 10px;text-decoration:none}.alternate:hover,.url:hover{color:var(--accent)}.note{color:var(--muted);font-size:.78rem;margin:22px 0 0}.note code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}a:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
          @media(max-width:700px){.site-header,main{width:min(calc(100% - 30px),1280px)}.stats{grid-template-columns:1fr}.stat{padding:18px 20px}main{padding:54px 0}h1{font-size:clamp(2.7rem,15vw,4.2rem)}}
          @media(prefers-color-scheme:dark){:root{color-scheme:dark;--ink:#edf2f5;--paper:#09131e;--surface:#111f2c;--muted:#aab6c0;--line:#edf2f538;--accent:#ff7b51;--mint:#285451}th{background:#0b1928;color:#fffdf8}.skip{background:#edf2f5;color:#09131e}}
        </style>
      </head>
      <body>
        <a class="skip" href="#content">Skip to sitemap</a>
        <header class="site-header">
          <a class="wordmark" href="/" aria-label="PDM — Paolo De Marinis, home">PDM<span>.</span></a>
          <span class="xml-label">XML Sitemap</span>
        </header>
        <main id="content">
          <p class="eyebrow">SEO / XML sitemap</p>
          <h1>Canonical pages.</h1>
          <p class="intro">This sitemap lists the public pages intended for Google Search, together with their English and Italian alternatives.</p>
          <section class="stats" aria-label="Sitemap summary">
            <div class="stat"><strong><xsl:value-of select="count(sm:urlset/sm:url)" /></strong><span>canonical URLs</span></div>
            <div class="stat"><strong>2</strong><span>languages</span></div>
            <div class="stat"><strong>XML</strong><span>standard sitemap format</span></div>
          </section>
          <div class="table-wrap">
            <table>
              <thead><tr><th scope="col">URL</th><th scope="col">Last significant update</th><th scope="col">Language versions</th></tr></thead>
              <tbody>
                <xsl:for-each select="sm:urlset/sm:url">
                  <tr>
                    <td><a class="url"><xsl:attribute name="href"><xsl:value-of select="sm:loc" /></xsl:attribute><xsl:value-of select="sm:loc" /></a></td>
                    <td class="date"><xsl:choose><xsl:when test="sm:lastmod"><xsl:value-of select="sm:lastmod" /></xsl:when><xsl:otherwise>—</xsl:otherwise></xsl:choose></td>
                    <td><div class="alternates"><xsl:for-each select="xhtml:link"><a class="alternate"><xsl:attribute name="href"><xsl:value-of select="@href" /></xsl:attribute><xsl:value-of select="@hreflang" /></a></xsl:for-each></div></td>
                  </tr>
                </xsl:for-each>
              </tbody>
            </table>
          </div>
          <p class="note">The stylesheet affects only browser presentation. Crawlers still receive the standard <code>urlset</code> XML data.</p>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
