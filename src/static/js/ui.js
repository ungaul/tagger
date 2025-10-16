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
    $("<div>")
      .addClass("cover")
      .html("<img class='header-label' src=static/img/cover.png>")
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
    $("<p>").addClass("header-label delete-column").text("Delete")
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

  if (music.metadata.cover_base_64) {
    $cover.attr(
      "src",
      `data:image/jpeg;base64,${music.metadata.cover_base_64}`
    );
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
    if (
      confirm(
        `Are you sure you want to delete "${filename}"? This cannot be undone.`
      )
    ) {
      deleteMusic(filename);
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
        $row.data("cover_base_64", base64);
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

  if ($row.data("cover_base_64")) {
    data.cover_base_64 = $row.data("cover_base_64");
  }

  return saveMusic(oldFilename, data).always(() => {
    $row.removeClass("dirty");
    $row.removeData("cover_base_64");
    if (data.new_filename) {
      $row.data("filename", data.new_filename);
    }
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
  fetchMusics({ offset })
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

let currentSortBy = getQueryParam("sort_by") || "title";
let currentSortOrder = getQueryParam("sort_order") || "asc";

function loadBatchSorted() {
  if (loading || noMore) return;
  loading = true;
  $("#loading").show().text("Loading...");

  fetchSortedMusics({
    offset,
    sort_by: currentSortBy,
    sort_order: currentSortOrder,
    q: $("#searchbar").val().trim(),
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
    .always(() => {
      loading = false;
      if (noMore) $("#loading").hide();
    });

  setQueryParam("sort_by", currentSortBy);
  setQueryParam("sort_order", currentSortOrder);
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