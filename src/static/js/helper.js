function notification(msg) {
  const $n = $("#notification");
  $n.text(msg).addClass("active");
  clearTimeout($n.data("timeout"));
  const timeout = setTimeout(() => {
    $n.removeClass("active");
  }, 3000);
  $n.data("timeout", timeout);
}

function getQueryParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param) || "";
}

function setQueryParam(param, value) {
  const url = new URL(window.location);
  if (value) url.searchParams.set(param, value);
  else url.searchParams.delete(param);
  history.replaceState(null, "", url.toString());
}
