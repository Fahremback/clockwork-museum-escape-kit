/* Lightweight, dependency-free gallery of genuine product PDF previews. */
(() => {
  "use strict";
  const image = document.getElementById("gallery-image");
  const caption = document.getElementById("gallery-caption");
  const picks = [...document.querySelectorAll(".gallery-pick")];
  const dialog = document.getElementById("preview-lightbox");
  const largeImage = document.getElementById("lightbox-image");
  const open = document.getElementById("open-preview");
  const close = document.getElementById("close-preview");
  if (!image || !caption || !dialog || !largeImage || !open || !close) return;
  let lastFocus = null;

  for (const pick of picks) {
    pick.addEventListener("click", () => {
      const src = pick.dataset.src;
      if (!/^assets\/[\w-]+\.webp$/.test(src || "")) return;
      image.src = src;
      image.alt = pick.dataset.alt || "Real product preview";
      image.dataset.wide = pick.dataset.wide || "false";
      caption.textContent = pick.dataset.label || "Real product PDF sample";
      for (const item of picks) item.setAttribute("aria-pressed", String(item === pick));
    });
  }

  const hide = () => {
    dialog.hidden = true;
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  };

  open.addEventListener("click", () => {
    lastFocus = document.activeElement;
    largeImage.src = image.src;
    largeImage.alt = image.alt;
    dialog.hidden = false;
    document.body.style.overflow = "hidden";
    close.focus();
  });
  close.addEventListener("click", hide);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) hide();
  });
  document.addEventListener("keydown", (event) => {
    if (dialog.hidden) return;
    if (event.key === "Escape") hide();
    if (event.key === "Tab") {
      event.preventDefault();
      close.focus();
    }
  });
})();
