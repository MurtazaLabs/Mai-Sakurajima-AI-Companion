(function () {
  var page = document.currentScript && document.currentScript.getAttribute("data-page");
  if (page) {
    location.replace("/desktop#space=" + page);
  }
})();
