function getQueryParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param) || "";
}

function setQueryParam(param, value) {
  const url = new URL(window.location);
  if (value) {
    url.searchParams.set(param, value);
  } else {
    url.searchParams.delete(param);
  }
  history.replaceState(null, "", url.toString());
}

$("#search").on("click", () => {
  $("#searchbar-container").toggleClass("active");
  if ($("#searchbar-container").hasClass("active")) {
    $("#searchbar").focus();
  }
});

$("#searchbar").on("keypress", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    const query = $("#searchbar").val().trim();

    offset = 0;
    noMore = false;

    setQueryParam("q", query);

    if (query === "") {
      $("#music-list").empty();
      loadBatch();
    } else {
      performSearch(query);
    }
  }
});

function performSearch(q) {
  if (loading || noMore) {
    return;
  }
  loading = true;
  $("#loading").show().text("Searching...");

  $.getJSON("/api/music", { offset, q })
    .done((data) => {
      if (offset === 0) {
        $("#music-list").empty().append(createHeaderRow());
      }
      data.musics.forEach((music) => {
        $("#music-list").append(createMusicRow(music));
      });
      offset += data.musics.length;
      noMore = !data.more;
      $("#loading").text(noMore ? "No more music" : "");
    })
    .fail(() => {
      $("#loading").text("Search failed");
    })
    .always(() => {
      loading = false;
      if (noMore) $("#loading").hide();
    });
}