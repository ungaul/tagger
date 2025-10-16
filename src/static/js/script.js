const PAGE_SIZE = 25;
let offset = 0;
let loading = false;
let noMore = false;

const METADATA_FIELDS = [
  {
    key: "filename",
    keys: ["filename"],
  },
  {
    key: "title",
    keys: [
      "title",
      "TIT2",
      "©nam",
      "TXXX:title",
      "TXXX:©nam",
    ],
  },
  {
    key: "artist",
    keys: [
      "artist",
      "TPE1",
      "TPE2",
      "TXXX:©ART",
      "TXXX:artist",
      "TXXX:ARTISTS",
      "TSO2",
      "TSOP",
    ],
  },
  { key: "tsrc", keys: ["TSRC", "TXXX:tsrc"] },

  {
    key: "publisher",
    keys: ["TMED", "TXXX:publisher"],
  },
  {
    key: "producers",
    keys: ["TEXT", "TXXX:producers"],
  },
  {
    key: "album",
    keys: ["album", "TALB", "©alb", "TXXX:album", "TXXX:©alb"],
  },
  {
    key: "year",
    keys: ["year", "TDRC", "TDOR", "©day", "TXXX:originalyear", "TXXX:©day", "TXXX:year"],
  },
  {
    key: "genre",
    keys: ["genre", "TCON", "©gen", "TXXX:©gen", "TXXX:genre"],
  },
  {
    key: "track",
    keys: ["tracknumber", "TRCK", "TPOS", "TXXX:track"],
  },
  { key: "bpm", keys: ["TBPM", "TXXX:bpm"] },
  { key: "key", keys: ["TKEY", "TXXX:key"] },
  { key: "length", keys: ["TLEN", "TXXX:length"] },
  { key: "label", keys: ["TPUB", "TCOP", "TXXX:label"] },
  { key: "musicbrainz_artist_id", keys: ["TXXX:MusicBrainz Artist Id", "TXXX:musicbrainz_artist_id"] },
  { key: "musicbrainz_album_id", keys: ["TXXX:MusicBrainz Album Id", "TXXX:musicbrainz_album_id"] },
  { key: "spotify_url", keys: ["WOAS", "TXXX:spotify_url"] },
  { key: "barcode", keys: ["TXXX:BARCODE", "TXXX:barcode"] },
  { key: "catalog_number", keys: ["TXXX:CATALOGNUMBER", "TXXX:catalog_number"] },
  { key: "asin", keys: ["TXXX:ASIN", "TXXX:asin"] },
  { key: "media_type", keys: ["TMED"] },

  {
    key: "musicbrainz_album_release_country",
    keys: ["TXXX:MusicBrainz Album Release Country", "TXXX:musicbrainz_album_release_country"],
  },
  { key: "musicbrainz_album_status", keys: ["TXXX:MusicBrainz Album Status", "TXXX:musicbrainz_album_status"] },
  { key: "musicbrainz_album_type", keys: ["TXXX:MusicBrainz Album Type", "TXXX:musicbrainz_album_type"] },
  {
    key: "musicbrainz_album_artist_id",
    keys: ["TXXX:MusicBrainz Album Artist Id", "TXXX:musicbrainz_album_artist_id"],
  },
  {
    key: "musicbrainz_release_group_id",
    keys: ["TXXX:MusicBrainz Release Group Id", "TXXX:musicbrainz_release_group_id"],
  },
  {
    key: "musicbrainz_release_track_id",
    keys: ["TXXX:MusicBrainz Release Track Id", "TXXX:musicbrainz_release_track_id"],
  },
  { key: "script", keys: ["TXXX:SCRIPT", "TXXX:script"] },
  { key: "ufid", keys: ["UFID:http://musicbrainz.org", "TXXX:ufid"] },

  {
    key: "comment",
    keys: ["COMM:ID3v1 Comment", "COMM", "TXXX:comment"],
  },
  {
    key: "description",
    keys: ["TXXX:description", "COMM:desc"],
  },
  { key: "likes", keys: ["TXXX:likes"] },
  { key: "dislikes", keys: ["TXXX:dislikes"] },
  { key: "software", keys: ["TSSE"] },
  { key: "views", keys: ["TXXX:views"] },
  { key: "rating", keys: ["TXXX:rating"] },
  { key: "download_date", keys: ["TXXX:download_date"] },
  { key: "uploader", keys: ["TXXX:uploader"] },
  {
    key: "purl",
    keys: ["TXXX:purl", "TXXX:comment"],
  },
  { key: "synopsis", keys: ["TXXX:synopsis"] },
  { key: "acoustid_id", keys: ["TXXX:Acoustid Id"] },
  { key: "copyright", keys: ["TCOP"] },
  { key: "involved_people", keys: ["TIPL"] },
  { key: "lyrics", keys: ["LYRICS"] },
];

function getFirstAvailable(metadata, keys) {
  for (const k of keys) {
    if (metadata.hasOwnProperty(k)) {
      const val = metadata[k];
      if (Array.isArray(val)) {
        if (val.length > 0 && val[0] !== "") return val[0];
      } else if (val !== undefined && val !== null && val !== "") {
        return val;
      }
    }
  }
  return "";
}

function createHeaderRow() {
  const $header = $("<div>").addClass("music-row header-row");
  $header.append(
    $("<div>").addClass("cover").html("<img class='header-label' src=static/img/cover.png>")
  );
  const $metaHeader = $("<div>").addClass("metadata");
  METADATA_FIELDS.forEach((f) => {
    $metaHeader.append(
      $("<p>")
        .addClass(`header-label ${f.key}`)
        .text(f.key.charAt(0).toUpperCase() + f.key.slice(1))
    );
  });

  $metaHeader.append(
    $("<p>")
      .addClass("header-label delete-column")
      .text("Delete")
  );

  $header.append($metaHeader);
  return $header;
}

function createMusicRow(music) {
  music.metadata.filename = music.filename;
  const $row = $("<div>")
    .addClass("music-row")
    .attr("data-filename", music.filename);

  const $coverWrapper = $("<div>").addClass("cover-wrapper");
  const $cover = $("<img>")
    .addClass("cover")
    .attr("title", "Click to change cover");

  if (music.metadata.cover_base64) {
    $cover.attr("src", `data:image/jpeg;base64,${music.metadata.cover_base64}`);
  } else {
    $cover.attr(
      "src",
      "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjZGRkZGRkIi8+PHRleHQgeD0iNDAiIHk9IjQ1IiBmb250LXNpemU9IjEyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjNzc3Ij5ObyBDb3ZlcjwvdGV4dD48L3N2Zz4="
    );
  }
  $coverWrapper.append($cover);
  $row.append($coverWrapper);

  const $metaContainer = $("<div>").addClass("metadata");
  METADATA_FIELDS.forEach((f) => {
    const val = getFirstAvailable(music.metadata, f.keys);
    const $input = $("<input>")
      .addClass(f.key)
      .attr("type", "text")
      .attr("class", f.key)
      .attr("placeholder", f.key)
      .val(val);
    $input.on("input", () => $row.addClass("dirty"));
    $metaContainer.append($input);
  });

  const $deleteCell = $("<div>").addClass("delete-column");
  const $deleteBtn = $("<ion-icon>")
    .attr("name", "trash-outline")
    .addClass("delete-btn")
    .attr("title", "Delete this music");
  $deleteCell.append($deleteBtn);
  $metaContainer.append($deleteCell);

  $row.append($metaContainer);

  $deleteCell.on("click", () => {
    const filename = $row.data("filename");
    if (confirm(`Are you sure you want to delete "${filename}"? This cannot be undone.`)) {
      $.ajax({
        url: "/api/music/delete",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ filename }),
      })
        .done(() => {
          notification(`Deleted "${filename}"`);
          $row.remove();
        })
        .fail((xhr) => {
          notification(`Failed to delete "${filename}": ${xhr.responseJSON?.error || xhr.statusText}`);
        });
    }
  });

  $cover.on("click", () => {
    const $fileInput = $(
      '<input type="file" accept="image/*" style="display:none;">'
    );
    $fileInput.on("change", () => {
      if ($fileInput[0].files.length === 0) return;
      const file = $fileInput[0].files[0];
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(",")[1];
        $cover.attr("src", reader.result);
        $row.addClass("dirty");
        $row.data("cover_base64", base64);
      };
      reader.readAsDataURL(file);
      $fileInput.remove();
    });
    $("body").append($fileInput);
    $fileInput.click();
  });

  return $row;
}

function saveRow($row) {
  const oldFilename = $row.data("filename");
  const data = {};
  $row.find(".metadata input").each(function () {
    const key = $(this).attr("class");
    data[key] = $(this).val();
  });
  if (data.filename && data.filename !== oldFilename) {
    data.new_filename = data.filename;
  }

  if ($row.data("cover_base64")) {
    data.cover_base64 = $row.data("cover_base64");
  }

  return $.ajax({
    url: `/api/music/${encodeURIComponent(oldFilename)}`,
    method: "POST",
    contentType: "application/json",
    data: JSON.stringify(data),
  })
    .done(() => {
      $row.removeClass("dirty");
      $row.removeData("cover_base64");
      if (data.new_filename) {
        $row.data("filename", data.new_filename);
      }

      notification("Saved " + (data.new_filename || oldFilename));
    })
    .fail(() => {
      notification("Failed to save " + oldFilename);
    });
}

function saveAllEdited() {
  const $dirtyRows = $(".music-row.dirty");
  if ($dirtyRows.length === 0) {
    notification("No changes to save.");
    return;
  }
  $dirtyRows.each(function () {
    saveRow($(this));
  });
}

function loadBatch() {
  if (loading || noMore) return;
  loading = true;
  $("#loading").show().text("Loading...");
  $.getJSON("/api/music", { offset })
    .done((data) => {
      if (offset === 0 && data.musics.length > 0) {
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
}

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