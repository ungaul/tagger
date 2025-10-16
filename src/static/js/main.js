const PAGE_SIZE = 25;
let offset = 0;
let loading = false;
let noMore = false;

$(function () {
  const query = getQueryParam("q").trim();
  $("#searchbar").val(query);

  offset = 0;
  noMore = false;

  loadBatchSorted();

  $("#searchbar").on("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      offset = 0;
      noMore = false;
      loadBatchSorted();
    }
  });

  $("#save").on("click", saveAllEdited);
  $("#load-more").on("click", () => {
    if (!loading && !noMore) {
      loadBatchSorted();
    }
  });
});
