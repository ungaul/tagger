function deleteMusic(filename) {
  if (!confirm(`Delete file "${filename}"? This action is irreversible.`))
    return;

  $.ajax({
    url: "/api/music/delete",
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify({ filename }),
  })
    .done(() => {
      notification(`Deleted ${filename}`);
      $(`.music-row[data-filename="${filename}"]`).remove();
    })
    .fail((xhr) => {
      notification(
        `Failed to delete ${filename}: ${
          xhr.responseJSON?.error || xhr.statusText
        }`
      );
    });
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

let currentSortBy = getQueryParam("sort_by") || "title";
let currentSortOrder = getQueryParam("sort_order") || "asc";

function loadBatchSorted() {
  if (loading || noMore) return;
  loading = true;
  $("#loading").show().text("Loading...");

  $.getJSON("/api/music", {
    offset,
    sort_by: currentSortBy,
    sort_order: currentSortOrder,
    q: $("#searchbar").val().trim()
  })
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
      $("#loading").text("Failed to load music");
    })
    .always(() => {
      loading = false;
      if (noMore) $("#loading").hide();
    });

  setQueryParam("sort_by", currentSortBy);
  setQueryParam("sort_order", currentSortOrder);
}