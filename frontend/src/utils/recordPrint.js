function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

function renderMetaRows(metaRows) {
  return metaRows.map((row) => {
    const cells = [...row]
    while (cells.length < 4) {
      cells.push("")
    }
    return `
      <tr>
        <th>${escapeHtml(cells[0])}</th>
        <td>${escapeHtml(cells[1])}</td>
        <th>${escapeHtml(cells[2])}</th>
        <td>${escapeHtml(cells[3])}</td>
      </tr>
    `
  }).join("")
}

function renderSections(sections) {
  return sections.map((section) => `
    <section class="print-section">
      <div class="print-section-title">${escapeHtml(section.heading)}</div>
      <div class="print-section-content">${escapeHtml(section.content || "")}</div>
    </section>
  `).join("")
}

function renderSignatures(signatures) {
  return `
    <div class="signature-row">
      ${signatures.map((item) => `
        <div class="signature-item">
          <span class="signature-label">${escapeHtml(item.label)}</span>
          <span class="signature-line"></span>
        </div>
      `).join("")}
    </div>
  `
}

export function openRecordPrintPreview({ title, subtitle, fileTitle, metaRows, sections, signatures, footerText }) {
  const previewWindow = window.open("", "_blank", "noopener,noreferrer,width=1000,height=900")
  if (!previewWindow) {
    throw new Error("PRINT_WINDOW_BLOCKED")
  }

  const signatureItems = signatures && signatures.length
    ? signatures
    : [{ label: "记录人签名" }, { label: "审核人签名" }, { label: "日期" }]

  const html = `
    <!DOCTYPE html>
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>${escapeHtml(fileTitle || title)}</title>
        <style>
          @page {
            size: A4;
            margin: 16mm 14mm;
          }

          * {
            box-sizing: border-box;
          }

          body {
            margin: 0;
            background: #eef2f7;
            color: #1f2937;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
          }

          .toolbar {
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            justify-content: center;
            gap: 12px;
            padding: 14px 16px;
            background: rgba(238, 242, 247, 0.95);
            border-bottom: 1px solid #d9e2ec;
            backdrop-filter: blur(8px);
          }

          .toolbar button {
            padding: 10px 18px;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            background: #fff;
            color: #0f172a;
            cursor: pointer;
            font-size: 14px;
          }

          .toolbar button.primary {
            background: #0f766e;
            border-color: #0f766e;
            color: #fff;
          }

          .page-wrap {
            padding: 24px 0 40px;
          }

          .page {
            width: 210mm;
            min-height: 297mm;
            margin: 0 auto;
            padding: 16mm 14mm;
            background: #fff;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
          }

          .record-title {
            text-align: center;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 1px;
          }

          .record-subtitle {
            margin: 6px 0 18px;
            text-align: center;
            color: #475569;
            font-size: 13px;
          }

          .meta-table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
            font-size: 13px;
          }

          .meta-table th,
          .meta-table td {
            border: 1px solid #475569;
            padding: 8px 10px;
            vertical-align: top;
            word-break: break-all;
          }

          .meta-table th {
            width: 15%;
            background: #f8fafc;
            font-weight: 700;
            text-align: left;
          }

          .meta-table td {
            width: 35%;
          }

          .print-section {
            margin-top: 16px;
          }

          .print-section-title {
            padding: 8px 10px;
            border: 1px solid #475569;
            border-bottom: none;
            background: #f8fafc;
            font-weight: 700;
            font-size: 14px;
          }

          .print-section-content {
            min-height: 96px;
            padding: 12px 14px;
            border: 1px solid #475569;
            white-space: pre-wrap;
            line-height: 1.75;
            font-size: 13px;
          }

          .signature-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            margin-top: 24px;
            align-items: end;
          }

          .signature-item {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
          }

          .signature-label {
            white-space: nowrap;
            font-weight: 600;
          }

          .signature-line {
            flex: 1;
            min-width: 80px;
            border-bottom: 1px solid #475569;
            height: 24px;
          }

          .page-footer {
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #94a3b8;
            text-align: right;
            color: #475569;
            font-size: 12px;
          }

          @media print {
            body {
              background: #fff;
            }

            .toolbar {
              display: none;
            }

            .page-wrap {
              padding: 0;
            }

            .page {
              width: auto;
              min-height: auto;
              margin: 0;
              padding: 0;
              box-shadow: none;
            }
          }
        </style>
      </head>
      <body>
        <div class="toolbar no-print">
          <button class="primary" onclick="window.print()">打印</button>
          <button onclick="window.close()">关闭</button>
        </div>
        <div class="page-wrap">
          <div class="page">
            <div class="record-title">${escapeHtml(title)}</div>
            <div class="record-subtitle">${escapeHtml(subtitle || "")}</div>
            <table class="meta-table">
              <tbody>
                ${renderMetaRows(metaRows)}
              </tbody>
            </table>
            ${renderSections(sections)}
            ${renderSignatures(signatureItems)}
            <div class="page-footer">${escapeHtml(footerText || "")}</div>
          </div>
        </div>
      </body>
    </html>
  `

  previewWindow.document.open()
  previewWindow.document.write(html)
  previewWindow.document.close()
  previewWindow.focus()
}