document.querySelectorAll("#desktop-cards .desk-card[data-nav]").forEach(function(el) {
  el.addEventListener("click", function() {
    if (window.MaiRouter) window.MaiRouter.navigateTo(el.getAttribute("data-nav"));
  });
});
