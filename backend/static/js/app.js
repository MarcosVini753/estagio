document.addEventListener("alpine:init", () => {
  Alpine.data("swipeNavigator", () => ({
    startX: 0,
    startY: 0,
    pointerId: null,
    suppressTrustedClicksUntil: 0,

    start(event) {
      if (!["touch", "pen"].includes(event.pointerType)) return;
      this.startX = event.clientX;
      this.startY = event.clientY;
      this.pointerId = event.pointerId;
    },

    cancel() {
      this.pointerId = null;
    },

    blockAccidentalClick(event) {
      if (
        event.isTrusted &&
        window.performance.now() < this.suppressTrustedClicksUntil
      ) {
        event.preventDefault();
        event.stopPropagation();
      }
    },

    finish(event) {
      if (this.pointerId === null || event.pointerId !== this.pointerId) return;
      const deltaX = event.clientX - this.startX;
      const deltaY = event.clientY - this.startY;
      this.pointerId = null;
      if (Math.abs(deltaX) < 56 || Math.abs(deltaX) <= Math.abs(deltaY) * 1.25) {
        return;
      }

      const selector =
        deltaX < 0
          ? this.$el.dataset.swipeNextSelector
          : this.$el.dataset.swipePrevSelector;
      if (!selector) return;
      const destination = document.querySelector(selector);
      if (!destination) return;

      event.preventDefault();
      this.suppressTrustedClicksUntil = window.performance.now() + 500;
      const content = document.getElementById("screen-content");
      const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      if (content && !reducedMotion) {
        content.classList.add(deltaX < 0 ? "screen-exit-left" : "screen-exit-right");
        window.setTimeout(() => destination.click(), 90);
      } else {
        destination.click();
      }
    },
  }));
});

function appDialog() {
  return document.getElementById("app-dialog");
}

function openAppDialog() {
  const dialog = appDialog();
  if (dialog && !dialog.open) dialog.showModal();
}

function closeAppDialog() {
  const dialog = appDialog();
  if (dialog?.open) dialog.close();
}

document.addEventListener("click", (event) => {
  if (event.target.closest("[data-dialog-close]")) closeAppDialog();
  const dialog = appDialog();
  if (dialog && event.target === dialog) closeAppDialog();
});

document.body.addEventListener("htmx:beforeSwap", (event) => {
  if (event.detail.xhr.status >= 400 && event.detail.xhr.status < 500) {
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  }
});

document.body.addEventListener("htmx:afterSwap", (event) => {
  if (event.detail.target.id === "app-dialog-content") openAppDialog();
  if (event.detail.target.id === "screen-content") {
    event.detail.target.focus({ preventScroll: true });
  }
});
