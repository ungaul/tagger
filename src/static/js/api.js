function login(username, password) {
  return $.ajax({
    url: "/login",
    method: "POST",
    contentType: "application/json",
    xhrFields: { withCredentials: true },
    data: JSON.stringify({ username, password }),
  });
}

function checkAuth() {
  return $.ajax({
    url: "/api/music",
    method: "GET",
    xhrFields: { withCredentials: true },
  });
}

function fetchMusics(params) {
  return $.getJSON("/api/music", params);
}

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

function saveMusic(oldFilename, data) {
  return $.ajax({
    url: `/api/music/${encodeURIComponent(oldFilename)}`,
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(data),
  })
    .done(() => {
      notification("Saved " + (data.new_filename || oldFilename));
    })
    .fail(() => {
      notification("Failed to save " + oldFilename);
    });
}

function searchMusic(query, offset) {
  return $.getJSON("/api/music", { offset, q: query });
}

function fetchMetadataFields() {
  return $.getJSON("/api/tags").fail(() => {
    notification("Failed to load metadata fields");
  });
}

let METADATA_FIELDS = [];
$(function () {
  fetchMetadataFields()
    .done((fieldsObj) => {
      METADATA_FIELDS = Object.entries(fieldsObj).map(([key, keys]) => ({
        key,
        keys,
      }));

      offset = 0;
      noMore = false;
      loadBatchSorted();
    })
    .fail(() => {});
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

function fetchSortedMusics({ offset, sort_by, sort_order, q }) {
  return $.getJSON("/api/music", { offset, sort_by, sort_order, q }).fail(
    () => {
      $("#loading").text("Failed to load music");
    }
  );
}
