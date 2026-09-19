/**
 * Export and Copy Page Markdown for AI Agents
 * Compatible with MkDocs Material instant navigation (document$)
 */

function setupExportMarkdownButtons() {
  const copyBtn = document.getElementById("copy-markdown-btn");
  const downloadBtn = document.getElementById("download-markdown-btn");
  const rawTextarea = document.getElementById("__raw_page_markdown__");

  if (!rawTextarea) return;

  const markdownContent = rawTextarea.value;

  if (copyBtn) {
    copyBtn.onclick = function (e) {
      e.preventDefault();
      const btnText = document.getElementById("copy-btn-text");
      const originalText = btnText ? btnText.textContent : "Copy Page as Markdown for AI";

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(markdownContent).then(showCopiedState, fallbackCopy);
      } else {
        fallbackCopy();
      }

      function fallbackCopy() {
        rawTextarea.style.display = "block";
        rawTextarea.select();
        try {
          document.execCommand("copy");
          showCopiedState();
        } catch (err) {
          console.error("Failed to copy markdown: ", err);
          alert("Could not copy automatically. Please select text manually.");
        } finally {
          rawTextarea.style.display = "none";
        }
      }

      function showCopiedState() {
        if (btnText) {
          btnText.textContent = "✓ Copied Markdown!";
        }
        copyBtn.style.backgroundColor = "var(--md-typeset-a-color, #10b981)";
        copyBtn.style.borderColor = "var(--md-typeset-a-color, #10b981)";

        setTimeout(() => {
          if (btnText) {
            btnText.textContent = originalText;
          }
          copyBtn.style.backgroundColor = "";
          copyBtn.style.borderColor = "";
        }, 2500);
      }
    };
  }

  if (downloadBtn) {
    downloadBtn.onclick = function (e) {
      e.preventDefault();
      const pageHeading = document.querySelector("h1");
      const pageTitle = pageHeading
        ? pageHeading.textContent.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "-")
        : "page";
      const filename = `${pageTitle}.md`;

      const blob = new Blob([markdownContent], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    };
  }
}

// Attach on standard DOM load and on MkDocs Material instant navigation
if (typeof document$ !== "undefined") {
  document$.subscribe(setupExportMarkdownButtons);
} else {
  document.addEventListener("DOMContentLoaded", setupExportMarkdownButtons);
}
